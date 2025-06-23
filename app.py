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
import uuid
from io import BytesIO

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max

# Template CSS pour le billet
TICKET_CSS = """
@page {
    size: 180mm 70mm;
    margin: 0;
    padding: 0;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    width: 180mm;
    height: 70mm;
    overflow: hidden;
    position: relative;
}

.ticket-container {
    width: 100%;
    height: 100%;
    display: flex;
    position: relative;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f1419 100%);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.ticket-left {
    width: 60%;
    height: 100%;
    position: relative;
    background: linear-gradient(135deg, rgba(26, 26, 46, 0.95) 0%, rgba(22, 33, 62, 0.9) 100%);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 16px 20px;
    overflow: hidden;
}

.event-bg {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0.3;
    z-index: 1;
}

.content-overlay {
    position: relative;
    z-index: 2;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.event-header {
    flex-shrink: 0;
}

.event-title {
    font-size: 22px;
    font-weight: 700;
    color: #ffd700;
    margin-bottom: 8px;
    line-height: 1.2;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}

.event-info {
    color: #ffffff;
    font-size: 12px;
    line-height: 1.4;
}

.info-row {
    display: flex;
    align-items: center;
    margin-bottom: 4px;
    background: rgba(255, 255, 255, 0.1);
    padding: 4px 8px;
    border-radius: 6px;
    backdrop-filter: blur(5px);
}

.info-icon {
    width: 16px;
    height: 16px;
    margin-right: 8px;
    opacity: 0.9;
}

.event-footer {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-shrink: 0;
}

.ticket-type {
    background: linear-gradient(45deg, #ffd700, #ffed4a);
    color: #1a1a2e;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    box-shadow: 0 4px 12px rgba(255, 215, 0, 0.4);
}

.organizer-info {
    color: #ffffff;
    font-size: 9px;
    text-align: right;
    opacity: 0.8;
}

.ticket-right {
    width: 40%;
    height: 100%;
    background: linear-gradient(45deg, #ffd700 0%, #ffed4a 100%);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    position: relative;
}

.ticket-right::before {
    content: '';
    position: absolute;
    left: -8px;
    top: 50%;
    transform: translateY(-50%);
    width: 16px;
    height: 16px;
    background: #1a1a2e;
    border-radius: 50%;
    box-shadow: 0 0 0 3px #ffd700;
}

.qr-section {
    text-align: center;
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.qr-code {
    width: 80px;
    height: 80px;
    border: 3px solid #1a1a2e;
    border-radius: 8px;
    margin-bottom: 8px;
    background: white;
    padding: 4px;
}

.qr-label {
    font-size: 8px;
    color: #1a1a2e;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.ticket-details {
    width: 100%;
    text-align: center;
    background: rgba(26, 26, 46, 0.1);
    padding: 8px;
    border-radius: 8px;
    margin-top: 8px;
}

.ticket-reference {
    font-size: 10px;
    color: #1a1a2e;
    font-weight: 700;
    margin-bottom: 4px;
    font-family: 'Courier New', monospace;
}

.ticket-price {
    font-size: 14px;
    color: #1a1a2e;
    font-weight: 900;
    text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
}

.ticket-count {
    font-size: 8px;
    color: #1a1a2e;
    opacity: 0.7;
    margin-top: 2px;
}

.perforated-edge {
    position: absolute;
    left: 60%;
    top: 0;
    bottom: 0;
    width: 2px;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 4px,
        #ffffff 4px,
        #ffffff 6px
    );
    z-index: 10;
}

.watermark {
    position: absolute;
    bottom: 4px;
    right: 8px;
    font-size: 6px;
    color: rgba(255, 255, 255, 0.3);
    z-index: 3;
}

@media print {
    body { margin: 0; }
    .ticket-container { 
        break-inside: avoid; 
        page-break-inside: avoid;
    }
}
"""

# Template HTML pour le billet
TICKET_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Billet - {{ ticket.event_title }}</title>
</head>
<body>
    <div class="ticket-container">
        <div class="ticket-left">
            {% if ticket.event_image_url %}
            <img src="{{ ticket.event_image_url }}" alt="Event" class="event-bg">
            {% endif %}
            
            <div class="content-overlay">
                <div class="event-header">
                    <h1 class="event-title">{{ ticket.event_title }}</h1>
                    <div class="event-info">
                        <div class="info-row">
                            <span>📅</span>
                            <span>{{ ticket.event_date_time }}</span>
                        </div>
                        <div class="info-row">
                            <span>📍</span>
                            <span>{{ ticket.event_location }}</span>
                        </div>
                        {% if ticket.event_address %}
                        <div class="info-row">
                            <span>🏠</span>
                            <span>{{ ticket.event_address }}</span>
                        </div>
                        {% endif %}
                    </div>
                </div>
                
                <div class="event-footer">
                    <div class="ticket-type">{{ ticket.ticket_type }}</div>
                    <div class="organizer-info">
                        <div>{{ ticket.organizer_name }}</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="perforated-edge"></div>
        
        <div class="ticket-right">
            <div class="qr-section">
                <img src="{{ ticket.qr_code }}" alt="QR Code" class="qr-code">
                <div class="qr-label">Scanner pour valider</div>
            </div>
            
            <div class="ticket-details">
                <div class="ticket-reference">{{ ticket.reference }}</div>
                <div class="ticket-price">{{ ticket.ticket_price }}</div>
                {% if ticket.total_tickets > 1 %}
                <div class="ticket-count">{{ ticket.current_ticket }}/{{ ticket.total_tickets }}</div>
                {% endif %}
            </div>
        </div>
        
        <div class="watermark">{{ ticket.generated_at }}</div>
    </div>
</body>
</html>
"""

# Template pour tickets multiples
MULTIPLE_TICKETS_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Billets - {{ tickets[0].event_title }}</title>
</head>
<body>
    {% for ticket in tickets %}
    <div class="ticket-container" style="{% if not loop.first %}page-break-before: always;{% endif %}">
        <div class="ticket-left">
            {% if ticket.event_image_url %}
            <img src="{{ ticket.event_image_url }}" alt="Event" class="event-bg">
            {% endif %}
            
            <div class="content-overlay">
                <div class="event-header">
                    <h1 class="event-title">{{ ticket.event_title }}</h1>
                    <div class="event-info">
                        <div class="info-row">
                            <span>📅</span>
                            <span>{{ ticket.event_date_time }}</span>
                        </div>
                        <div class="info-row">
                            <span>📍</span>
                            <span>{{ ticket.event_location }}</span>
                        </div>
                        {% if ticket.event_address %}
                        <div class="info-row">
                            <span>🏠</span>
                            <span>{{ ticket.event_address }}</span>
                        </div>
                        {% endif %}
                    </div>
                </div>
                
                <div class="event-footer">
                    <div class="ticket-type">{{ ticket.ticket_type }}</div>
                    <div class="organizer-info">
                        <div>{{ ticket.organizer_name }}</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="perforated-edge"></div>
        
        <div class="ticket-right">
            <div class="qr-section">
                <img src="{{ ticket.qr_code }}" alt="QR Code" class="qr-code">
                <div class="qr-label">Scanner pour valider</div>
            </div>
            
            <div class="ticket-details">
                <div class="ticket-reference">{{ ticket.reference }}</div>
                <div class="ticket-price">{{ ticket.ticket_price }}</div>
                {% if ticket.total_tickets > 1 %}
                <div class="ticket-count">{{ ticket.current_ticket }}/{{ ticket.total_tickets }}</div>
                {% endif %}
            </div>
        </div>
        
        <div class="watermark">{{ ticket.generated_at }}</div>
    </div>
    {% endfor %}
</body>
</html>
"""

def validate_ticket_data(data):
    """Valide les données du billet"""
    required_fields = [
        'event_title', 'event_date_time', 'event_location',
        'ticket_type', 'ticket_price', 'organizer_name',
        'qr_code', 'reference'
    ]
    
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"Champ requis manquant: {field}")
    
    # Validation des formats
    if not isinstance(data.get('current_ticket', 1), int):
        data['current_ticket'] = 1
    if not isinstance(data.get('total_tickets', 1), int):
        data['total_tickets'] = 1
        
    return data

def process_image_url(image_url):
    """Traite l'URL de l'image pour s'assurer qu'elle est accessible"""
    if not image_url:
        return None
        
    try:
        # Si c'est déjà une URL data ou une URL complète, la retourner
        if image_url.startswith(('data:', 'http://', 'https://')):
            return image_url
            
        # Sinon, considérer comme un chemin relatif
        return image_url
        
    except Exception as e:
        logger.warning(f"Erreur traitement image URL: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de santé du service"""
    return jsonify({
        'status': 'healthy',
        'service': 'PDF Ticket Generator',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/generate-ticket', methods=['POST'])
def generate_single_ticket():
    """Génère un billet unique"""
    try:
        data = request.get_json()
        
        if not data or 'ticket' not in data:
            return jsonify({'error': 'Données de billet requises'}), 400
            
        ticket_data = validate_ticket_data(data['ticket'])
        
        # Traitement de l'image
        if 'event_image_url' in ticket_data:
            ticket_data['event_image_url'] = process_image_url(ticket_data['event_image_url'])
        
        # Options de format
        format_options = data.get('format', {})
        pdf_options = data.get('options', {})
        
        # Rendu HTML
        html_content = render_template_string(TICKET_HTML_TEMPLATE, ticket=ticket_data)
        
        # Génération PDF
        html_doc = HTML(string=html_content)
        css_doc = CSS(string=TICKET_CSS)
        
        # Configuration WeasyPrint
        pdf_buffer = io.BytesIO()
        html_doc.write_pdf(
            pdf_buffer,
            stylesheets=[css_doc],
            presentational_hints=pdf_options.get('enable_forms', True)
        )
        
        pdf_buffer.seek(0)
        
        logger.info(f"Billet généré avec succès: {ticket_data.get('reference', 'N/A')}")
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"billet-{ticket_data.get('reference', 'ticket')}.pdf"
        )
        
    except ValueError as e:
        logger.error(f"Erreur de validation: {e}")
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        logger.error(f"Erreur génération billet: {e}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500

@app.route('/generate-multiple-tickets', methods=['POST'])
def generate_multiple_tickets():
    """Génère plusieurs billets en un seul PDF"""
    try:
        data = request.get_json()
        
        if not data or 'tickets' not in data or not isinstance(data['tickets'], list):
            return jsonify({'error': 'Liste de billets requise'}), 400
            
        if len(data['tickets']) == 0:
            return jsonify({'error': 'Au moins un billet requis'}), 400
            
        if len(data['tickets']) > 50:  # Limite de sécurité
            return jsonify({'error': 'Maximum 50 billets par requête'}), 400
        
        # Validation de tous les billets
        validated_tickets = []
        for i, ticket in enumerate(data['tickets']):
            try:
                validated_ticket = validate_ticket_data(ticket)
                if 'event_image_url' in validated_ticket:
                    validated_ticket['event_image_url'] = process_image_url(validated_ticket['event_image_url'])
                validated_tickets.append(validated_ticket)
            except ValueError as e:
                return jsonify({'error': f'Erreur billet {i+1}: {str(e)}'}), 400
        
        # Options
        format_options = data.get('format', {})
        pdf_options = data.get('options', {})
        
        # Rendu HTML
        html_content = render_template_string(MULTIPLE_TICKETS_HTML_TEMPLATE, tickets=validated_tickets)
        
        # Génération PDF
        html_doc = HTML(string=html_content)
        css_doc = CSS(string=TICKET_CSS)
        
        pdf_buffer = io.BytesIO()
        html_doc.write_pdf(
            pdf_buffer,
            stylesheets=[css_doc],
            presentational_hints=pdf_options.get('enable_forms', True)
        )
        
        pdf_buffer.seek(0)
        
        logger.info(f"Billets multiples générés: {len(validated_tickets)} billets")
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"billets-{validated_tickets[0].get('reference', 'tickets')}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Erreur génération billets multiples: {e}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500

@app.route('/preview-ticket', methods=['POST'])
def preview_ticket():
    """Génère un aperçu HTML du billet"""
    try:
        data = request.get_json()
        
        if not data or 'ticket' not in data:
            return jsonify({'error': 'Données de billet requises'}), 400
            
        ticket_data = validate_ticket_data(data['ticket'])
        
        if 'event_image_url' in ticket_data:
            ticket_data['event_image_url'] = process_image_url(ticket_data['event_image_url'])
        
        html_content = render_template_string(TICKET_HTML_TEMPLATE, ticket=ticket_data)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>{TICKET_CSS}</style>
            <title>Aperçu Billet</title>
        </head>
        <body style="background: #f0f0f0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh;">
            {html_content}
        </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"Erreur aperçu: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Gestionnaire d'erreurs HTTP"""
    return jsonify({
        'error': e.description,
        'code': e.code
    }), e.code

@app.errorhandler(Exception)
def handle_exception(e):
    """Gestionnaire d'erreurs générales"""
    logger.error(f"Erreur non gérée: {e}")
    return jsonify({
        'error': 'Erreur interne du serveur',
        'message': str(e) if app.debug else 'Une erreur est survenue'
    }), 500

if __name__ == '__main__':
    # Configuration pour le développement
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    )