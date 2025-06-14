from flask import Flask, request, send_file, render_template, jsonify
from weasyprint import HTML, CSS
import io
import logging
from datetime import datetime
import os
from werkzeug.exceptions import HTTPException

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
        ticket_data.update({
            'generated_at': datetime.utcnow().isoformat(),
            'current_ticket': data.get('current_ticket', 1),
            'total_tickets': data.get('total_tickets', 1),
            'format': data.get('format', DEFAULT_FORMAT)
        })
        
        try:
            html = render_template("ticket_template.html", **ticket_data)
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
    .ticket-container {
        width: 100%;
        height: 100%;
        display: flex;
    }
    .ticket-left {
        width: 120mm;
        height: 70mm;
        background: linear-gradient(rgba(15, 26, 61, 0.85), rgba(15, 26, 61, 0.9));
        color: white;
        padding: 10mm;
        display: flex;
        flex-direction: column;
    }
    /* Ajoutez ici le reste du CSS fourni ci-dessus */
""")
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
                'details': str(e)
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
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        
        if not data or 'tickets' not in data:
            return jsonify({'error': 'Tickets array is required'}), 400
            
        tickets = data['tickets']
        format = data.get('format', DEFAULT_FORMAT)
        
        if not isinstance(tickets, list):
            return jsonify({'error': 'Tickets must be an array'}), 400
            
        if len(tickets) > MAX_TICKETS_PER_REQUEST:
            return jsonify({
                'error': f'Too many tickets (max {MAX_TICKETS_PER_REQUEST})',
                'received': len(tickets)
            }), 413
            
        generated_at = datetime.utcnow().isoformat()
        total_tickets = len(tickets)
        
        html_pages = []
        for idx, ticket in enumerate(tickets, start=1):
            try:
                ticket.update({
                    'generated_at': generated_at,
                    'current_ticket': idx,
                    'total_tickets': total_tickets,
                    'format': format
                })
                html = render_template("ticket_template.html", **ticket)
                html_pages.append(html)
            except Exception as e:
                logger.error(f"Erreur avec le ticket {idx}: {str(e)}")
                continue
        
        if not html_pages:
            return jsonify({'error': 'No valid tickets to generate'}), 400
        
        try:
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
    .ticket-container {
        width: 100%;
        height: 100%;
        display: flex;
    }
    .ticket-left {
        width: 120mm;
        height: 70mm;
        background: linear-gradient(rgba(15, 26, 61, 0.85), rgba(15, 26, 61, 0.9));
        color: white;
        padding: 10mm;
        display: flex;
        flex-direction: column;
    }
    /* Ajoutez ici le reste du CSS fourni ci-dessus */
""")
            pdf_docs = [HTML(string=html).render(stylesheets=[css]) for html in html_pages]
            main_doc = pdf_docs[0]
            
            for doc in pdf_docs[1:]:
                main_doc.pages.extend(doc.pages)
            
            pdf_bytes = main_doc.write_pdf()
            
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
                'details': str(e)
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