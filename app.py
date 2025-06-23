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
import requests

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max

# Template CSS amélioré pour le billet
TICKET_CSS = """
@page {
    size: 210mm 85mm;
    margin: 0;
    padding: 0;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    width: 210mm;
    height: 85mm;
    overflow: hidden;
    position: relative;
    background: #ffffff;
}

.ticket-container {
    width: 100%;
    height: 100%;
    display: flex;
    position: relative;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.ticket-left {
    width: 65%;
    height: 100%;
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 24px 28px;
    overflow: hidden;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.95) 0%, rgba(118, 75, 162, 0.95) 100%);
}

.event-bg {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0.15;
    z-index: 1;
    filter: blur(1px);
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
    margin-bottom: 16px;
}

.event-title {
    font-size: 28px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 12px;
    line-height: 1.1;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    letter-spacing: -0.5px;
}

.event-info {
    color: #ffffff;
    font-size: 14px;
    line-height: 1.5;
    margin-bottom: 16px;
}

.info-row {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    background: rgba(255, 255, 255, 0.15);
    padding: 8px 12px;
    border-radius: 10px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all 0.3s ease;
}

.info-row:hover {
    background: rgba(255, 255, 255, 0.2);
}

.info-icon {
    font-size: 16px;
    margin-right: 10px;
    opacity: 0.9;
    width: 20px;
    text-align: center;
}

.info-text {
    font-weight: 500;
    flex: 1;
}

.event-footer {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-shrink: 0;
    margin-top: auto;
}

.ticket-type {
    background: linear-gradient(45deg, #ff6b6b, #ff8e8e);
    color: #ffffff;
    padding: 10px 18px;
    border-radius: 25px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
    border: 2px solid rgba(255, 255, 255, 0.2);
}

.organizer-info {
    color: #ffffff;
    font-size: 11px;
    text-align: right;
    opacity: 0.9;
    font-weight: 500;
}

.ticket-right {
    width: 35%;
    height: 100%;
    background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    padding: 20px 16px;
    position: relative;
    border-left: 2px dashed rgba(102, 126, 234, 0.3);
}

.ticket-right::before {
    content: '';
    position: absolute;
    left: -10px;
    top: 50%;
    transform: translateY(-50%);
    width: 20px;
    height: 20px;
    background: #ffffff;
    border-radius: 50%;
    box-shadow: 0 0 0 4px #667eea;
    z-index: 5;
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
    width: 100px;
    height: 100px;
    border: 3px solid #667eea;
    border-radius: 12px;
    margin-bottom: 12px;
    background: white;
    padding: 6px;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
}

.qr-label {
    font-size: 10px;
    color: #667eea;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    text-align: center;
    line-height: 1.3;
}

.ticket-details {
    width: 100%;
    text-align: center;
    background: rgba(102, 126, 234, 0.08);
    padding: 12px;
    border-radius: 12px;
    margin-top: 16px;
    border: 1px solid rgba(102, 126, 234, 0.1);
}

.ticket-reference {
    font-size: 11px;
    color: #667eea;
    font-weight: 700;
    margin-bottom: 6px;
    font-family: 'Courier New', monospace;
    letter-spacing: 1px;
}

.ticket-price {
    font-size: 18px;
    color: #2d3748;
    font-weight: 900;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    margin-bottom: 4px;
}

.ticket-count {
    font-size: 9px;
    color: #667eea;
    opacity: 0.8;
    font-weight: 500;
}

.perforated-edge {
    position: absolute;
    left: 65%;
    top: 0;
    bottom: 0;
    width: 2px;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 6px,
        rgba(102, 126, 234, 0.3) 6px,
        rgba(102, 126, 234, 0.3) 8px
    );
    z-index: 10;
}

.watermark {
    position: absolute;
    bottom: 8px;
    right: 12px;
    font-size: 7px;
    color: rgba(255, 255, 255, 0.4);
    z-index: 3;
    font-weight: 500;
}

.gradient-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, 
        rgba(102, 126, 234, 0.1) 0%, 
        rgba(118, 75, 162, 0.1) 50%,
        rgba(255, 107, 107, 0.05) 100%);
    z-index: 1;
    pointer-events: none;
}

@media print {
    body { margin: 0; }
    .ticket-container { 
        break-inside: avoid; 
        page-break-inside: avoid;
    }
}

/* Animations subtiles */
.ticket-container {
    animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
"""

# Template HTML amélioré pour le billet
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
        <div class="gradient-overlay"></div>
        
        <div class="ticket-left">
            {% if ticket.event_image_url %}
            <img src="{{ ticket.event_image_url }}" alt="Event Background" class="event-bg">
            {% endif %}
            
            <div class="content-overlay">
                <div class="event-header">
                    <h1 class="event-title">{{ ticket.event_title }}</h1>
                    <div class="event-info">
                        <div class="info-row">
                            <span class="info-icon">📅</span>
                            <span class="info-text">{{ ticket.event_date_time }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">📍</span>
                            <span class="info-text">{{ ticket.event_location }}</span>
                        </div>
                        {% if ticket.event_address %}
                        <div class="info-row">
                            <span class="info-icon">🏠</span>
                            <span class="info-text">{{ ticket.event_address }}</span>
                        </div>
                        {% endif %}
                    </div>
                </div>
                
                <div class="event-footer">
                    <div class="ticket-type">{{ ticket.ticket_type }}</div>
                    <div class="organizer-info">
                        <div>Organisé par</div>
                        <div style="font-weight: 700; margin-top: 2px;">{{ ticket.organizer_name }}</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="perforated-edge"></div>
        
        <div class="ticket-right">
            <div class="qr-section">
                <img src="{{ ticket.qr_code }}" alt="QR Code" class="qr-code">
                <div class="qr-label">Scanner pour<br>valider l'entrée</div>
            </div>
            
            <div class="ticket-details">
                <div class="ticket-reference">{{ ticket.reference }}</div>
                <div class="ticket-price">{{ ticket.ticket_price }}</div>
                {% if ticket.total_tickets > 1 %}
                <div class="ticket-count">Billet {{ ticket.current_ticket }} sur {{ ticket.total_tickets }}</div>
                {% endif %}
            </div>
        </div>
        
        <div class="watermark">Généré le {{ ticket.generated_at }}</div>
    </div>
</body>
</html>
"""

# Template pour tickets multiples amélioré
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
    <div class="ticket-container" style="{% if not loop.first %}page-break-before: always; margin-top: 20mm;{% endif %}">
        <div class="gradient-overlay"></div>
        
        <div class="ticket-left">
            {% if ticket.event_image_url %}
            <img src="{{ ticket.event_image_url }}" alt="Event Background" class="event-bg">
            {% endif %}
            
            <div class="content-overlay">
                <div class="event-header">
                    <h1 class="event-title">{{ ticket.event_title }}</h1>
                    <div class="event-info">
                        <div class="info-row">
                            <span class="info-icon">📅</span>
                            <span class="info-text">{{ ticket.event_date_time }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">📍</span>
                            <span class="info-text">{{ ticket.event_location }}</span>
                        </div>
                        {% if ticket.event_address %}
                        <div class="info-row">
                            <span class="info-icon">🏠</span>
                            <span class="info-text">{{ ticket.event_address }}</span>
                        </div>
                        {% endif %}
                    </div>
                </div>
                
                <div class="event-footer">
                    <div class="ticket-type">{{ ticket.ticket_type }}</div>
                    <div class="organizer-info">
                        <div>Organisé par</div>
                        <div style="font-weight: 700; margin-top: 2px;">{{ ticket.organizer_name }}</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="perforated-edge"></div>
        
        <div class="ticket-right">
            <div class="qr-section">
                <img src="{{ ticket.qr_code }}" alt="QR Code" class="qr-code">
                <div class="qr-label">Scanner pour<br>valider l'entrée</div>
            </div>
            
            <div class="ticket-details">
                <div class="ticket-reference">{{ ticket.reference }}</div>
                <div class="ticket-price">{{ ticket.ticket_price }}</div>
                {% if ticket.total_tickets > 1 %}
                <div class="ticket-count">Billet {{ ticket.current_ticket }} sur {{ ticket.total_tickets }}</div>
                {% endif %}
            </div>
        </div>
        
        <div class="watermark">Généré le {{ ticket.generated_at }}</div>
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
    
    # Ajout de la date de génération si non présente
    if 'generated_at' not in data:
        data['generated_at'] = datetime.now().strftime("%d/%m/%Y à %H:%M")
        
    return data

def process_image_url(image_url):
    """Traite l'URL de l'image pour s'assurer qu'elle est accessible"""
    if not image_url:
        return None
        
    try:
        # Si c'est déjà une URL data, la retourner
        if image_url.startswith('data:'):
            return image_url
            
        # Si c'est une URL HTTP/HTTPS, essayer de la télécharger et la convertir en base64
        if image_url.startswith(('http://', 'https://')):
            try:
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                
                # Déterminer le type MIME
                content_type = response.headers.get('content-type', '')
                if 'image' not in content_type:
                    logger.warning(f"URL ne semble pas être une image: {content_type}")
                    return None
                
                # Convertir en base64
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                return f"data:{content_type};base64,{image_base64}"
                
            except Exception as e:
                logger.warning(f"Impossible de télécharger l'image: {e}")
                return None
        
        # Sinon, considérer comme un chemin local
        return image_url
        
    except Exception as e:
        logger.warning(f"Erreur traitement image URL: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de santé du service"""
    return jsonify({
        'status': 'healthy',
        'service': 'Enhanced PDF Ticket Generator',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

@app.route('/generate-ticket', methods=['POST'])
def generate_single_ticket():
    """Génère un billet unique"""
    try:
        data = request.get_json()
        
        if not data or 'ticket' not in data:
            return jsonify({'error': 'Données de billet requises'}), 400
            
        ticket_data = validate_ticket_data(data['ticket'])
        
        # Traitement de l'image avec gestion d'erreur améliorée
        if 'event_image_url' in ticket_data and ticket_data['event_image_url']:
            processed_image = process_image_url(ticket_data['event_image_url'])
            ticket_data['event_image_url'] = processed_image
        
        # Options de format
        format_options = data.get('format', {})
        pdf_options = data.get('options', {})
        
        # Rendu HTML
        html_content = render_template_string(TICKET_HTML_TEMPLATE, ticket=ticket_data)
        
        # Génération PDF avec options améliorées
        html_doc = HTML(string=html_content)
        css_doc = CSS(string=TICKET_CSS)
        
        # Configuration WeasyPrint améliorée
        pdf_buffer = io.BytesIO()
        html_doc.write_pdf(
            pdf_buffer,
            stylesheets=[css_doc],
            presentational_hints=pdf_options.get('enable_forms', True),
            optimize_images=True
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
                if 'event_image_url' in validated_ticket and validated_ticket['event_image_url']:
                    processed_image = process_image_url(validated_ticket['event_image_url'])
                    validated_ticket['event_image_url'] = processed_image
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
            presentational_hints=pdf_options.get('enable_forms', True),
            optimize_images=True
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
        
        if 'event_image_url' in ticket_data and ticket_data['event_image_url']:
            processed_image = process_image_url(ticket_data['event_image_url'])
            ticket_data['event_image_url'] = processed_image
        
        html_content = render_template_string(TICKET_HTML_TEMPLATE, ticket=ticket_data)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>{TICKET_CSS}</style>
            <title>Aperçu Billet - {ticket_data.get('event_title', 'Événement')}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <div style="transform: scale(0.8); transform-origin: center;">
                {html_content}
            </div>
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