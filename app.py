from flask import Flask, request, send_file, render_template_string, jsonify
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
import json

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
MAX_IMAGE_SIZE = 1024 * 1024  # 1MB max pour les images
TEMP_DIR = tempfile.mkdtemp(prefix='pdf_service_')

CORS(app)

# Template HTML amélioré intégré
TICKET_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
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
    }

    body {
      width: 180mm;
      height: 70mm;
      margin: 0;
      padding: 0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      overflow: hidden;
      background: white;
      position: relative;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }

    .ticket-container {
      width: 100%;
      height: 100%;
      position: relative;
      display: table;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
    }

    .ticket-main {
      position: relative;
      width: 140mm;
      height: 100%;
      float: left;
      background: linear-gradient(135deg, 
        rgba(15, 26, 61, 0.95) 0%, 
        rgba(42, 59, 113, 0.9) 30%, 
        rgba(15, 26, 61, 0.95) 100%);
      color: white;
      padding: 8mm;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      overflow: hidden;
    }

    .ticket-main::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      {% if event_image_url %}
      background-image: url('{{ event_image_url }}');
      {% else %}
      background-image: url('https://images.unsplash.com/photo-1540575467063-178a50c2df87?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=85');
      {% endif %}
      background-size: cover;
      background-position: center;
      opacity: 0.3;
      z-index: 0;
    }

    .ticket-main::after {
      content: "";
      position: absolute;
      top: 10mm;
      bottom: 10mm;
      right: 0;
      width: 2px;
      background: repeating-linear-gradient(
        to bottom,
        transparent 0,
        transparent 3mm,
        rgba(255,215,0,0.8) 3mm,
        rgba(255,215,0,0.8) 5mm,
        transparent 5mm,
        transparent 8mm
      );
      z-index: 1;
    }

    .ticket-content {
      position: relative;
      z-index: 2;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .event-header {
      margin-bottom: 3mm;
    }

    .event-title {
      font-size: 7mm;
      font-weight: 800;
      margin: 0 0 2mm 0;
      line-height: 1.1;
      letter-spacing: -0.5px;
      text-transform: uppercase;
      text-shadow: 2px 2px 8px rgba(0,0,0,0.5);
      color: #FFD700;
    }

    .event-date-wrapper {
      display: flex;
      align-items: center;
      gap: 2mm;
      background: rgba(255,255,255,0.15);
      padding: 2mm 3mm;
      border-radius: 8px;
      border: 1px solid rgba(255,215,0,0.3);
      backdrop-filter: blur(10px);
    }

    .event-date {
      font-size: 3.5mm;
      font-weight: 600;
      margin: 0;
      color: white;
    }

    .event-details {
      background: rgba(0,0,0,0.3);
      padding: 3mm;
      border-radius: 8px;
      margin: 2mm 0;
      backdrop-filter: blur(5px);
    }

    .location-wrapper {
      display: flex;
      align-items: center;
      gap: 2mm;
      margin-bottom: 1mm;
    }

    .event-location {
      font-size: 4mm;
      font-weight: 600;
      margin: 0;
      color: white;
    }

    .event-address {
      font-size: 3mm;
      margin: 0;
      color: rgba(255,255,255,0.8);
      padding-left: 5.5mm;
    }

    .event-footer {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }

    .organizer-section {
      flex: 1;
    }

    .organizer-label {
      font-size: 2.5mm;
      color: rgba(255,255,255,0.7);
      margin: 0 0 1mm 0;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .organizer-name {
      font-size: 3.5mm;
      font-weight: 700;
      color: #FFD700;
      margin: 0;
    }

    .price-section {
      text-align: right;
    }

    .price-label {
      font-size: 2.5mm;
      color: rgba(255,255,255,0.7);
      margin: 0 0 1mm 0;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .ticket-price {
      font-size: 6mm;
      font-weight: 900;
      color: #FFD700;
      margin: 0;
      text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .ticket-stub {
      width: 40mm;
      height: 100%;
      float: right;
      background: linear-gradient(to bottom, #0F1A3D 0%, #2A3B71 50%, #1a237e 100%);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4mm;
      position: relative;
      color: white;
    }

    .ticket-stub::before {
      content: "";
      position: absolute;
      left: 0;
      top: 8mm;
      bottom: 8mm;
      width: 2px;
      background: repeating-linear-gradient(
        to bottom,
        transparent 0,
        transparent 3mm,
        rgba(255,215,0,0.8) 3mm,
        rgba(255,215,0,0.8) 5mm,
        transparent 5mm,
        transparent 8mm
      );
    }

    .ticket-type-label {
      font-size: 2.5mm;
      font-weight: 500;
      margin: 0 0 2mm 0;
      text-transform: uppercase;
      color: rgba(255,255,255,0.7);
      letter-spacing: 1px;
    }

    .ticket-type {
      font-size: 3.5mm;
      font-weight: 700;
      margin: 0 0 4mm 0;
      text-transform: uppercase;
      color: #FFD700;
      text-align: center;
    }

    .qr-wrapper {
      width: 22mm;
      height: 22mm;
      background: white;
      padding: 1.5mm;
      border-radius: 4px;
      margin: 2mm 0;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .qr-code {
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
    }

    .ticket-meta {
      text-align: center;
      margin-top: 3mm;
    }

    .ticket-number {
      font-size: 2.8mm;
      font-weight: 600;
      margin: 0 0 1mm 0;
      color: white;
    }

    .ticket-reference {
      font-size: 2.5mm;
      font-weight: 400;
      margin: 0;
      color: rgba(255,255,255,0.7);
      font-family: 'Courier New', monospace;
    }

    @media print {
      body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
      
      .ticket-container {
        box-shadow: none;
      }
    }
  </style>
</head>
<body>
  <div class="ticket-container">
    <div class="ticket-main">
      <div class="ticket-content">
        <div class="event-header">
          <h1 class="event-title">{{ event_title }}</h1>
          <div class="event-date-wrapper">
            <span>📅</span>
            <div class="event-date">{{ event_date_time }}</div>
          </div>
        </div>
        
        <div class="event-details">
          <div class="location-wrapper">
            <span>📍</span>
            <div class="event-location">{{ event_location }}</div>
          </div>
          {% if event_address %}
          <div class="event-address">{{ event_address }}</div>
          {% endif %}
        </div>
        
        <div class="event-footer">
          <div class="organizer-section">
            <div class="organizer-label">Organisé par</div>
            <div class="organizer-name">{{ organizer_name }}</div>
          </div>
          <div class="price-section">
            <div class="price-label">Prix</div>
            <div class="ticket-price">{{ ticket_price }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="ticket-stub">
      <div class="ticket-type-label">Billet</div>
      <div class="ticket-type">{{ ticket_type }}</div>
      
      <div class="qr-wrapper">
        {% if qr_code %}
          <img src="{{ qr_code }}" alt="QR Code" class="qr-code">
        {% else %}
          <div class="qr-placeholder">
            <span>⚡</span>
          </div>
        {% endif %}
      </div>
      
      <div class="ticket-meta">
        <div class="ticket-number">{{ current_ticket }}/{{ total_tickets }}</div>
        <div class="ticket-reference">{{ reference }}</div>
      </div>
    </div>
  </div>
</body>
</html>"""

def optimize_image(image_data, max_size=MAX_IMAGE_SIZE):
    """Optimise une image en base64 pour WeasyPrint"""
    try:
        if len(image_data) > max_size:
            # Décoder et optimiser l'image
            image_bytes = base64.b64decode(image_data)
            
            with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp:
                tmp.write(image_bytes)
                tmp.flush()
                
                with Image.open(tmp.name) as img:
                    # Convertir en RGB si nécessaire
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # Redimensionner si trop grand
                    if img.width > 1200 or img.height > 800:
                        img.thumbnail((1200, 800), Image.Resampling.LANCZOS)
                    
                    # Sauvegarder avec compression
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=85, optimize=True)
                    optimized_data = base64.b64encode(output.getvalue()).decode('utf-8')
                    
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

def validate_ticket_data(ticket_data):
    """Valide et nettoie les données du billet"""
    required_fields = ['event_title', 'reference']
    
    for field in required_fields:
        if field not in ticket_data or not ticket_data[field]:
            raise ValueError(f"Champ requis manquant: {field}")
    
    # Valeurs par défaut
    defaults = {
        'event_date_time': 'Date à définir',
        'event_location': 'Lieu de l\'événement',
        'event_address': '',
        'ticket_type': 'STANDARD',
        'ticket_price': 'GRATUIT',
        'organizer_name': 'Organisateur',
        'current_ticket': 1,
        'total_tickets': 1,
        'qr_code': None
    }
    
    for key, default_value in defaults.items():
        if key not in ticket_data:
            ticket_data[key] = default_value
    
    return ticket_data

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'running',
        'service': 'PDF Generator',
        'version': '2.0.0',
        'temp_dir': TEMP_DIR,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/generate', methods=['POST'])
def generate_pdf():
    """Endpoint pour générer un ou plusieurs billets PDF"""
    try:
        # Vérifier le content-type
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        
        # Valider les données d'entrée
        if not data or 'tickets' not in data:
            return jsonify({'error': 'No tickets data provided'}), 400
        
        tickets = data['tickets']
        format_config = data.get('format', DEFAULT_FORMAT)
        
        # Limiter le nombre de billets par requête
        if len(tickets) > MAX_TICKETS_PER_REQUEST:
            return jsonify({
                'error': f'Too many tickets in one request (max {MAX_TICKETS_PER_REQUEST})'
            }), 400

        # Préparer les options de format
        css = CSS(string=f"""
            @page {{ 
                size: {format_config.get('width', DEFAULT_FORMAT['width'])} 
                     {format_config.get('height', DEFAULT_FORMAT['height'])};
                margin: 0;
            }}
        """)

        # Générer les PDFs
        pdf_files = []
        for ticket in tickets:
            try:
                # Valider et nettoyer les données du billet
                ticket = validate_ticket_data(ticket)
                
                # Optimiser l'image si fournie
                if 'event_image_url' in ticket and ticket['event_image_url']:
                    if ticket['event_image_url'].startswith('data:image'):
                        ticket['event_image_url'] = optimize_image(
                            ticket['event_image_url'].split(',')[1]
                        )
                        ticket['event_image_url'] = f"data:image/jpeg;base64,{ticket['event_image_url']}"
                
                # Optimiser le QR code si fourni
                if 'qr_code' in ticket and ticket['qr_code']:
                    if ticket['qr_code'].startswith('data:image'):
                        ticket['qr_code'] = optimize_image(
                            ticket['qr_code'].split(',')[1],
                            max_size=512*1024  # Taille plus petite pour les QR codes
                        )
                        ticket['qr_code'] = f"data:image/jpeg;base64,{ticket['qr_code']}"
                
                # Rendre le template HTML avec les données du billet
                html = HTML(string=render_template_string(TICKET_TEMPLATE, **ticket))
                
                # Générer le PDF
                pdf_bytes = io.BytesIO()
                html.write_pdf(pdf_bytes, stylesheets=[css])
                pdf_files.append(pdf_bytes.getvalue())
                
            except Exception as e:
                logger.error(f"Error generating ticket {ticket.get('reference', 'unknown')}: {str(e)}")
                continue

        # Retourner le résultat
        if not pdf_files:
            return jsonify({'error': 'Failed to generate any tickets'}), 500
        
        if len(pdf_files) == 1:
            # Retourner un seul PDF
            return send_file(
                io.BytesIO(pdf_files[0]),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"ticket_{tickets[0].get('reference', 'unknown')}.pdf"
            )
        else:
            # Créer un ZIP avec plusieurs PDFs (implémentation optionnelle)
            # Pour l'exemple, nous retournons juste le premier PDF
            # Dans une implémentation réelle, vous pourriez utiliser zipfile
            return send_file(
                io.BytesIO(pdf_files[0]),
                mimetype='application/pdf',
                as_attachment=True,
                download_name="tickets.pdf"
            )

    except Exception as e:
        logger.error(f"Error in generate_pdf endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Gestion des erreurs HTTP"""
    logger.error(f"HTTP error: {e.code} - {e.description}")
    return jsonify({
        'error': e.description,
        'code': e.code
    }), e.code

@app.errorhandler(Exception)
def handle_exception(e):
    """Gestion des autres exceptions"""
    logger.error(f"Unexpected error: {str(e)}")
    return jsonify({
        'error': 'An unexpected error occurred',
        'details': str(e)
    }), 500

if __name__ == '__main__':
    # Nettoyer les fichiers temporaires au démarrage
    clean_temp_files()
    
    # Configurer le port et l'hôte
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Démarrer l'application
    app.run(host=host, port=port, debug=os.environ.get('DEBUG', 'false').lower() == 'true')