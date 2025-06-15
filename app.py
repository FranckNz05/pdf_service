from flask import Flask, request, send_file, render_template, jsonify
from weasyprint import HTML, CSS
import io
import logging
from datetime import datetime
import os
from werkzeug.exceptions import HTTPException
from flask_cors import CORS


app = Flask(__name__)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pdf_service.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
TEMPLATE_FOLDER = os.path.join(os.path.dirname(__file__), 'templates')
MAX_TICKETS_PER_REQUEST = 50
DEFAULT_FORMAT = {'width': '180mm', 'height': '70mm'}

CORS(app)
@app.route('/')
def health_check():
    return jsonify({
        'status': 'running',
        'service': 'PDF Generator',
        'version': '1.0.0',
        'endpoints': {
            'single_ticket': {'method': 'POST', 'path': '/generate-ticket'},
            'multiple_tickets': {'method': 'POST', 'path': '/generate-multiple-tickets'}
        }
    }), 200

@app.route('/generate-ticket', methods=['POST'])
def generate_ticket():
    try:
        if not request.is_json:
            logger.warning('Requête non-JSON reçue')
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        
        if not data or 'ticket' not in data:
            logger.warning('Données de ticket manquantes')
            return jsonify({'error': 'Ticket data is required'}), 400
            
        ticket_data = data['ticket']
        
        # Log des données reçues
        logger.info(f"Données ticket reçues - Référence: {ticket_data.get('reference', 'inconnue')}")
        logger.debug(f"Données complètes: { {k: v[:100] + '...' if isinstance(v, str) and len(v) > 100 else v for k, v in ticket_data.items()} }")
        
        # Vérification des images
        if 'event_image' in ticket_data:
            if ticket_data['event_image']:
                logger.info(f"Image événement reçue - Taille: {len(ticket_data['event_image'])} caractères")
            else:
                logger.warning("Aucune image événement reçue")
        
        if 'qr_code' in ticket_data:
            if ticket_data['qr_code']:
                logger.info(f"QR Code reçu - Taille: {len(ticket_data['qr_code'])} caractères")
            else:
                logger.warning("Aucun QR Code reçu")
        
        ticket_data.update({
            'generated_at': datetime.utcnow().isoformat(),
            'current_ticket': data.get('current_ticket', 1),
            'total_tickets': data.get('total_tickets', 1),
            'format': data.get('format', DEFAULT_FORMAT)
        })
        
        try:
            # Validation des données avant génération
            if not ticket_data.get('event_title'):
                logger.error("Titre d'événement manquant")
                return jsonify({'error': 'Event title is required'}), 400
                
            if not ticket_data.get('reference'):
                logger.error("Référence de ticket manquante")
                return jsonify({'error': 'Ticket reference is required'}), 400
                
            html = render_template("ticket_template.html", **ticket_data)
            
            # Log du HTML généré (partiel pour éviter la surcharge)
            logger.debug(f"HTML généré (extrait): {html[:500]}...")
            
            css = CSS(string="""
                @page {
                    size: 180mm 70mm;
                    margin: 0;
                    padding: 0;
                }
                body {
                    width: 180mm;
                    height: 70mm;
                    margin: 0;
                    padding: 0;
                    font-family: 'Montserrat', sans-serif;
                    overflow: hidden;
                }
                /* ... autres règles CSS ... */
            """)
            
            # Génération PDF avec vérification des images
            try:
                pdf = HTML(string=html).write_pdf(stylesheets=[css])
                logger.info("PDF généré avec succès")
            except Exception as e:
                logger.error(f"Erreur WeasyPrint: {str(e)}")
                # Tentative sans images en cas d'échec
                if 'event_image' in ticket_data:
                    ticket_data['event_image'] = None
                    logger.warning("Nouvelle tentative sans image événement")
                    html = render_template("ticket_template.html", **ticket_data)
                    pdf = HTML(string=html).write_pdf(stylesheets=[css])
                
            return send_file(
                io.BytesIO(pdf),
                mimetype='application/pdf',
                as_attachment=False,
                download_name=f'ticket_{ticket_data.get("reference", "unknown")}.pdf'
            )
            
        except Exception as e:
            logger.error(f"Erreur de génération PDF: {str(e)}", exc_info=True)
            return jsonify({
                'error': 'PDF generation failed',
                'details': str(e),
                'image_received': 'event_image' in ticket_data and bool(ticket_data['event_image']),
                'qr_received': 'qr_code' in ticket_data and bool(ticket_data['qr_code'])
            }), 500
            
    except Exception as e:
        logger.critical(f"Erreur inattendue: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'request_id': request.headers.get('X-Request-ID', 'none')
        }), 500

@app.route('/generate-multiple-tickets', methods=['POST'])
def generate_multiple_tickets():
    try:
        if not request.is_json:
            logger.warning("Requête non-JSON pour multiple tickets")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        
        if not data or 'tickets' not in data:
            logger.warning("Données tickets manquantes")
            return jsonify({'error': 'Tickets array is required'}), 400
            
        tickets = data['tickets']
        format = data.get('format', DEFAULT_FORMAT)
        
        logger.info(f"Demande de génération de {len(tickets)} tickets")
        
        if not isinstance(tickets, list):
            logger.error("Tickets n'est pas un tableau")
            return jsonify({'error': 'Tickets must be an array'}), 400
            
        if len(tickets) > MAX_TICKETS_PER_REQUEST:
            logger.warning(f"Trop de tickets demandés ({len(tickets)} > {MAX_TICKETS_PER_REQUEST})")
            return jsonify({
                'error': f'Too many tickets (max {MAX_TICKETS_PER_REQUEST})',
                'received': len(tickets)
            }), 413
            
        # Statistiques sur les images reçues
        tickets_with_images = sum(1 for t in tickets if t.get('event_image'))
        tickets_with_qr = sum(1 for t in tickets if t.get('qr_code'))
        
        logger.info(f"Statistiques - Tickets avec images: {tickets_with_images}/{len(tickets)}, QR codes: {tickets_with_qr}/{len(tickets)}")
        
        generated_at = datetime.utcnow().isoformat()
        total_tickets = len(tickets)
        
        html_pages = []
        errors = []
        for idx, ticket in enumerate(tickets, start=1):
            try:
                # Validation des données minimales
                if not ticket.get('event_title'):
                    raise ValueError("Missing event_title")
                if not ticket.get('reference'):
                    raise ValueError("Missing reference")
                
                ticket.update({
                    'generated_at': generated_at,
                    'current_ticket': idx,
                    'total_tickets': total_tickets,
                    'format': format
                })
                
                html = render_template("ticket_template.html", **ticket)
                html_pages.append(html)
                
            except Exception as e:
                error_msg = f"Erreur avec le ticket {idx} (ref: {ticket.get('reference', 'inconnue')}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        if not html_pages:
            logger.error("Aucun ticket valide à générer")
            return jsonify({
                'error': 'No valid tickets to generate',
                'details': errors
            }), 400
        
        try:
            css = CSS(string="""
                /* ... votre CSS existant ... */
            """)
            
            logger.info("Début de la génération PDF...")
            pdf_docs = [HTML(string=html).render(stylesheets=[css]) for html in html_pages]
            main_doc = pdf_docs[0]
            
            for doc in pdf_docs[1:]:
                main_doc.pages.extend(doc.pages)
            
            pdf_bytes = main_doc.write_pdf()
            logger.info("PDF multi-tickets généré avec succès")
            
            first_ref = tickets[0].get('reference', 'start')
            last_ref = tickets[-1].get('reference', 'end')
            
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=False,
                download_name=f'tickets_{first_ref}_to_{last_ref}.pdf'
            )
            
        except Exception as e:
            logger.error(f"Erreur de fusion PDF: {str(e)}", exc_info=True)
            return jsonify({
                'error': 'PDF merge failed',
                'details': str(e),
                'tickets_processed': len(html_pages),
                'errors': errors
            }), 500
            
    except Exception as e:
        logger.critical(f"Erreur inattendue (multi-tickets): {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'request_id': request.headers.get('X-Request-ID', 'none')
        }), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'Bad request',
        'message': str(error.description) if hasattr(error, 'description') else None
    }), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('DEBUG', 'false').lower() == 'true'
    )