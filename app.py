from flask import Flask, request, send_file, render_template_string, jsonify
from weasyprint import HTML, CSS
import io
import logging
from datetime import datetime
import os
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
import base64
import tempfile
import shutil
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import zlib
import time

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
MAX_TICKETS_PER_REQUEST = 50
DEFAULT_FORMAT = {'width': '180mm', 'height': '70mm'}
TEMP_DIR = tempfile.mkdtemp(prefix='pdf_service_')
MAX_WORKERS = 4  # Nombre de threads pour le traitement parallèle
CACHE_TTL = 3600  # 1 heure en secondes
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB max pour les images

CORS(app)

# Template HTML intégré (version optimisée basée sur celui de l'IA)
TICKET_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Billet d'événement</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

        @page {
            size: 180mm 70mm;
            margin: 0;
            padding: 0;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            width: 180mm;
            height: 70mm;
            font-family: 'Inter', sans-serif;
            overflow: hidden;
            background: white;
            position: relative;
        }

        .ticket-container {
            width: 100%;
            height: 100%;
            display: flex;
            border: 3px solid #1a237e;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            position: relative;
        }

        .ticket-left {
            width: 130mm;
            height: calc(70mm - 6px);
            position: relative;
            color: white;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 12mm;
            background: linear-gradient(135deg, #1a237e 0%, #3949ab 50%, #5c6bc0 100%);
            overflow: hidden;
        }

        .ticket-left::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url('{{ event_image_url }}');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            opacity: 0.3;
            z-index: 1;
        }

        .ticket-left > * {
            position: relative;
            z-index: 2;
        }

        .ticket-left::after {
            content: '';
            position: absolute;
            top: 8mm;
            right: -2px;
            bottom: 8mm;
            width: 4px;
            background: repeating-linear-gradient(
                to bottom,
                transparent 0px,
                transparent 4px,
                #ddd 4px,
                #ddd 8px
            );
            z-index: 3;
        }

        .event-header {
            margin-bottom: 6mm;
        }

        .event-title {
            font-size: 11mm;
            font-weight: 900;
            line-height: 0.9;
            margin-bottom: 4mm;
            text-transform: uppercase;
            letter-spacing: -0.5px;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.7);
            color: #ffffff;
        }

        .event-date-time {
            display: inline-flex;
            align-items: center;
            gap: 3mm;
            background: rgba(255,193,7,0.95);
            color: #1a237e;
            padding: 3mm 5mm;
            border-radius: 6mm;
            font-weight: 700;
            font-size: 5mm;
            box-shadow: 0 3px 12px rgba(0,0,0,0.3);
        }

        .event-details {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            gap: 3mm;
        }

        .location-info {
            display: flex;
            align-items: flex-start;
            gap: 3mm;
            background: rgba(0,0,0,0.2);
            padding: 4mm;
            border-radius: 6mm;
            backdrop-filter: blur(10px);
        }

        .location-icon {
            color: #ffc107;
            font-size: 5mm;
            margin-top: 1mm;
        }

        .location-text {
            flex-grow: 1;
        }

        .event-location {
            font-size: 5.5mm;
            font-weight: 700;
            margin-bottom: 1mm;
            color: #ffffff;
        }

        .event-address {
            font-size: 4mm;
            opacity: 0.9;
            font-weight: 400;
            color: #ffffff;
        }

        .event-footer {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-top: 4mm;
        }

        .organizer-info {
            display: flex;
            align-items: center;
            gap: 3mm;
            font-size: 4mm;
        }

        .organizer-name {
            font-weight: 700;
            color: #ffc107;
            font-size: 4.5mm;
        }

        .price-display {
            background: linear-gradient(135deg, #ffc107, #ff8f00);
            color: #1a237e;
            padding: 3mm 6mm;
            border-radius: 6mm;
            font-weight: 900;
            font-size: 7mm;
            box-shadow: 0 4px 15px rgba(255,193,7,0.4);
            text-align: center;
            min-width: 25mm;
        }

        .ticket-right {
            width: 50mm;
            height: calc(70mm - 6px);
            background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 6mm;
            position: relative;
            color: white;
        }

        .ticket-right::before {
            content: '';
            position: absolute;
            left: -2px;
            top: 8mm;
            bottom: 8mm;
            width: 4px;
            background: repeating-linear-gradient(
                to bottom,
                transparent 0px,
                transparent 4px,
                #ddd 4px,
                #ddd 8px
            );
        }

        .ticket-type-badge {
            background: #ffc107;
            color: #1a237e;
            padding: 2mm 4mm;
            border-radius: 4mm;
            font-weight: 800;
            font-size: 3.5mm;
            text-transform: uppercase;
            margin-bottom: 4mm;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }

        .qr-code-container {
            width: 32mm;
            height: 32mm;
            background: white;
            padding: 2mm;
            border-radius: 4mm;
            margin: 3mm 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .qr-code-container img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .qr-placeholder {
            width: 100%;
            height: 100%;
            background: #f5f5f5;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-size: 8mm;
            border-radius: 2mm;
        }

        .ticket-info {
            text-align: center;
            margin-top: 4mm;
            width: 100%;
        }

        .ticket-number {
            background: rgba(255,193,7,0.2);
            color: #ffc107;
            padding: 2mm 4mm;
            border-radius: 3mm;
            font-weight: 700;
            font-size: 3.5mm;
            margin-bottom: 2mm;
            border: 1px solid rgba(255,193,7,0.4);
        }

        .ticket-reference {
            font-family: 'Courier New', monospace;
            font-size: 3mm;
            letter-spacing: 1px;
            color: #b0bec5;
            background: rgba(0,0,0,0.2);
            padding: 1.5mm 3mm;
            border-radius: 2mm;
        }

        @media print {
            body {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            
            .ticket-container {
                page-break-inside: avoid;
            }
        }

        @media (max-width: 180mm) {
            .event-title { font-size: 9mm; }
            .event-date-time { font-size: 4mm; }
            .event-location { font-size: 4.5mm; }
            .price-display { font-size: 6mm; }
        }
    </style>
</head>
<body>
    <div class="ticket-container">
        <!-- Partie gauche -->
        <div class="ticket-left" style="--event-image: url('{{ event_image_url }}');">
            <div class="event-header">
                <h1 class="event-title">{{ event_title }}</h1>
                <div class="event-date-time">
                    <span>📅</span>
                    <span>{{ event_date_time }}</span>
                </div>
            </div>
            
            <div class="event-details">
                <div class="location-info">
                    <div class="location-icon">📍</div>
                    <div class="location-text">
                        <div class="event-location">{{ event_location }}</div>
                        <div class="event-address">{{ event_address }}</div>
                    </div>
                </div>
            </div>
            
            <div class="event-footer">
                <div class="organizer-info">
                    <span>👤</span>
                    <span>Organisé par</span>
                    <span class="organizer-name">{{ organizer_name }}</span>
                </div>
                <div class="price-display">{{ ticket_price }}</div>
            </div>
        </div>
        
        <!-- Partie droite -->
        <div class="ticket-right">
            <div class="ticket-type-badge">{{ ticket_type }}</div>
            
            <div class="qr-code-container">
                <img src="{{ qr_code }}" alt="QR Code d'accès" onerror="this.parentElement.innerHTML='<div class=\'qr-placeholder\'>QR</div>'">
            </div>
            
            <div class="ticket-info">
                <div class="ticket-number">Billet {{ current_ticket }}/{{ total_tickets }}</div>
                <div class="ticket-reference">{{ reference }}</div>
            </div>
        </div>
    </div>
</body>
</html>
"""

def clean_temp_files():
    """Nettoie les fichiers temporaires"""
    try:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
            os.makedirs(TEMP_DIR)
    except Exception as e:
        logger.error(f"Erreur de nettoyage des fichiers temporaires: {str(e)}")

def optimize_image(image_data, max_size=MAX_IMAGE_SIZE):
    """Optimise une image en base64 pour WeasyPrint"""
    try:
        if len(image_data) > max_size:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                tmp.write(base64.b64decode(image_data))
                tmp_path = tmp.name
            
            with Image.open(tmp_path) as img:
                # Réduire la taille si nécessaire
                if img.width > 1200 or img.height > 1200:
                    img.thumbnail((1200, 1200))
                
                # Convertir en JPEG pour réduire la taille
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Optimiser la qualité
                optimized_path = f"{tmp_path}_optimized.jpg"
                img.save(optimized_path, format='JPEG', quality=85, optimize=True, progressive=True)
                
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

def validate_ticket_data(ticket_data):
    """Valide les données du ticket"""
    required_fields = [
        'event_title', 'reference', 'qr_code',
        'event_date_time', 'event_location', 'organizer_name',
        'ticket_price', 'ticket_type'
    ]
    
    for field in required_fields:
        if not ticket_data.get(field):
            logger.error(f"Champ requis manquant: {field}")
            return False
    
    return True

def generate_pdf_from_html(html_content, format_data=None):
    """Génère un PDF à partir du contenu HTML"""
    try:
        start_time = time.time()
        
        # CSS minimal pour WeasyPrint
        css = CSS(string="""
            @page {
                size: 180mm 70mm;
                margin: 0;
                padding: 0;
            }
            body {
                margin: 0;
                padding: 0;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
        """)
        
        # Génération PDF avec options optimisées
        pdf = HTML(
            string=html_content,
            base_url=request.base_url
        ).write_pdf(
            stylesheets=[css],
            optimize_size=('fonts', 'images', 'content'),
            presentational_hints=True
        )
        
        logger.info(f"PDF généré en {time.time() - start_time:.2f}s")
        return pdf
        
    except Exception as e:
        logger.error(f"Erreur de génération PDF: {str(e)}", exc_info=True)
        raise

@app.route('/health')
def health_check():
    """Endpoint de vérification de santé"""
    return jsonify({
        'status': 'healthy',
        'service': 'PDF Generator',
        'version': '2.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/generate-ticket', methods=['POST'])
def generate_ticket():
    """Génère un ticket PDF unique"""
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
        
        # Validation des données
        if not validate_ticket_data(ticket_data):
            return jsonify({'error': 'Invalid ticket data'}), 400
        
        # Optimisation des images
        if 'event_image' in ticket_data and ticket_data['event_image']:
            ticket_data['event_image'] = optimize_image(ticket_data['event_image'])
            ticket_data['event_image_url'] = f"data:image/jpeg;base64,{ticket_data['event_image']}"
        else:
            ticket_data['event_image_url'] = 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=85'
        
        # Préparation des données
        ticket_data.update({
            'generated_at': datetime.utcnow().isoformat(),
            'current_ticket': data.get('current_ticket', 1),
            'total_tickets': data.get('total_tickets', 1),
            'format': data.get('format', DEFAULT_FORMAT)
        })
        
        # Génération HTML
        html = render_template_string(TICKET_TEMPLATE, **ticket_data)
        
        # Génération PDF
        pdf = generate_pdf_from_html(html)
        
        logger.info(f"Ticket généré - Référence: {ticket_data['reference']}")
        
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
    """Génère plusieurs tickets dans un seul PDF"""
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
        
        # CSS partagé pour tous les tickets
        css = CSS(string="""
            @page {
                size: 180mm 70mm;
                margin: 0;
                padding: 0;
            }
            body {
                margin: 0;
                padding: 0;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
        """)
        
        # Génération des PDF individuels en parallèle
        pdf_docs = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for idx, ticket in enumerate(tickets[:MAX_TICKETS_PER_REQUEST], start=1):
                try:
                    # Validation des champs requis
                    if not validate_ticket_data(ticket):
                        continue
                    
                    # Optimisation des images
                    if 'event_image' in ticket and ticket['event_image']:
                        ticket['event_image'] = optimize_image(ticket['event_image'])
                        ticket['event_image_url'] = f"data:image/jpeg;base64,{ticket['event_image']}"
                    else:
                        ticket['event_image_url'] = 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=85'
                    
                    ticket.update({
                        'generated_at': generated_at,
                        'current_ticket': idx,
                        'total_tickets': total_tickets,
                        'format': DEFAULT_FORMAT
                    })
                    
                    html = render_template_string(TICKET_TEMPLATE, **ticket)
                    futures.append(executor.submit(generate_pdf_from_html, html))
                    
                except Exception as e:
                    logger.error(f"Erreur avec le ticket {idx}: {str(e)}")
                    continue
            
            for future in as_completed(futures):
                try:
                    pdf_doc = HTML(string=render_template_string(TICKET_TEMPLATE)).render(stylesheets=[css])
                    pdf_docs.append(pdf_doc)
                except Exception as e:
                    logger.error(f"Erreur lors de la génération: {str(e)}")
        
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