from flask import Flask, request, send_file, render_template, jsonify
from weasyprint import HTML, CSS
import io
import logging
from datetime import datetime
import os
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
import base64
from PIL import Image
import tempfile
import shutil

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
MAX_IMAGE_SIZE = 1024 * 1024  # 1MB max pour les images
TEMP_DIR = tempfile.mkdtemp(prefix='pdf_service_')

CORS(app)

def optimize_image(image_data, max_size=MAX_IMAGE_SIZE):
    """Optimise une image en base64 pour WeasyPrint"""
    try:
        if len(image_data) > max_size:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                tmp.write(base64.b64decode(image_data))
                tmp_path = tmp.name
            
            with Image.open(tmp_path) as img:
                # Réduire la taille si nécessaire
                if img.width > 800 or img.height > 800:
                    img.thumbnail((800, 800))
                
                # Convertir en JPEG pour réduire la taille
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Optimiser la qualité
                optimized_path = f"{tmp_path}_optimized.jpg"
                img.save(optimized_path, format='JPEG', quality=85)
                
                with open(optimized_path, 'rb') as f:
                    optimized_data = base64.b64encode(f.read()).decode('utf-8')
                
                os.unlink(tmp_path)
                os.unlink(optimized_path)
                
                logger.info(f"Image optimisée: {len(image_data)} -> {len(optimized_data)} bytes")
                return optimized_data
        
        return image_data
    except Exception as e:
        logger.error(f"Erreur d'optimisation d'image: {str(e)}")
        return image_data

def clean_temp_files():
    """Nettoie les fichiers temporaires"""
    try:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
            os.makedirs(TEMP_DIR)
    except Exception as e:
        logger.error(f"Erreur de nettoyage des fichiers temporaires: {str(e)}")

@app.route('/')
def health_check():
    return jsonify({
        'status': 'running',
        'service': 'PDF Generator',
        'version': '1.1.1',
        'temp_dir': TEMP_DIR
    }), 200

@app.route('/generate-ticket', methods=['POST'])
def generate_ticket():
    clean_temp_files()
    
    try:
        if not request.is_json:
            logger.warning('Requête non-JSON reçue')
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        
        if not data or 'ticket' not in data:
            logger.warning('Données de ticket manquantes')
            return jsonify({'error': 'Ticket data is required'}), 400
            
        ticket_data = data['ticket']
        
        # Validation des données minimales
        required_fields = ['event_title', 'reference', 'qr_code']
        for field in required_fields:
            if field not in ticket_data or not ticket_data[field]:
                logger.error(f"Champ requis manquant: {field}")
                return jsonify({'error': f'Field {field} is required'}), 400
        
        # Optimisation des images
        if 'event_image' in ticket_data and ticket_data['event_image']:
            ticket_data['event_image'] = optimize_image(ticket_data['event_image'])
        
        # Préparation des données
        ticket_data.update({
            'generated_at': datetime.utcnow().isoformat(),
            'current_ticket': data.get('current_ticket', 1),
            'total_tickets': data.get('total_tickets', 1),
            'format': data.get('format', DEFAULT_FORMAT)
        })
        
        # Génération HTML
        html = render_template("ticket_template.html", **ticket_data)
        
        # CSS simplifié et compatible
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
                position: relative;
            }
            .ticket-left {
                width: 120mm;
                height: 70mm;
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                color: white;
                padding: 8mm 10mm;
                display: flex;
                flex-direction: column;
                box-sizing: border-box;
            }
            .qr-container img {
                width: 100%;
                height: 100%;
            }
        """)
        
        # Génération PDF avec options compatibles
        pdf = HTML(
            string=html,
            base_url=request.base_url
        ).write_pdf(stylesheets=[css])
        
        logger.info(f"PDF généré avec succès - Référence: {ticket_data['reference']}")
        
        return send_file(
            io.BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f'ticket_{ticket_data["reference"]}.pdf'
        )
            
    except Exception as e:
        logger.error(f"Erreur de génération PDF: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'PDF generation failed',
            'details': str(e)
        }), 500

@app.route('/generate-multiple-tickets', methods=['POST'])
def generate_multiple_tickets():
    clean_temp_files()
    
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        
        if not data or 'tickets' not in data:
            return jsonify({'error': 'Tickets array is required'}), 400
            
        tickets = data['tickets']
        
        # Validation de base
        if len(tickets) > MAX_TICKETS_PER_REQUEST:
            return jsonify({
                'error': f'Too many tickets (max {MAX_TICKETS_PER_REQUEST})',
                'received': len(tickets)
            }), 413
        
        # Préparation des données
        generated_at = datetime.utcnow().isoformat()
        total_tickets = len(tickets)
        format = data.get('format', DEFAULT_FORMAT)
        
        # CSS partagé pour tous les tickets
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
        """)
        
        # Génération des PDF individuels
        pdf_docs = []
        for idx, ticket in enumerate(tickets[:MAX_TICKETS_PER_REQUEST], start=1):
            try:
                # Validation des champs requis
                if not all(ticket.get(field) for field in ['event_title', 'reference', 'qr_code']):
                    continue
                
                # Optimisation des images
                if 'event_image' in ticket and ticket['event_image']:
                    ticket['event_image'] = optimize_image(ticket['event_image'])
                
                ticket.update({
                    'generated_at': generated_at,
                    'current_ticket': idx,
                    'total_tickets': total_tickets,
                    'format': format
                })
                
                html = render_template("ticket_template.html", **ticket)
                pdf_doc = HTML(string=html).render(stylesheets=[css])
                pdf_docs.append(pdf_doc)
                
            except Exception as e:
                logger.error(f"Erreur avec le ticket {idx}: {str(e)}")
                continue
        
        if not pdf_docs:
            return jsonify({'error': 'No valid tickets to generate'}), 400
        
        # Fusion des PDF
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
        logger.error(f"Erreur de génération multiple: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'PDF generation failed',
            'details': str(e)
        }), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    try:
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            threaded=True,
            debug=False
        )
    finally:
        clean_temp_files()