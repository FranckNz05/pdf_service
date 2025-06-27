from flask import Flask, request, send_file, render_template_string, jsonify
from weasyprint import HTML, CSS
import io
import logging
from datetime import datetime
import os
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
import base64
import requests

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max

# CSS pour le design de billet
TICKET_CSS = """
@import url("https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&family=Playfair+Display:wght@700&display=swap");
@import url("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css");

@page {
    size: 210mm 100mm;
    margin: 0;
    padding: 0;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body, html {
    height: 100vh;
    font-family: "Montserrat", sans-serif;
    background: #f5f5f5;
    color: #333;
    font-size: 14px;
}

.ticket {
    margin: 0 auto;
    display: flex;
    background: white;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
    width: 210mm;
    height: 100mm;
    position: relative;
    overflow: hidden;
    border-radius: 8px;
}

.left {
    display: flex;
    width: 70%;
    position: relative;
}

.left::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(to right, rgba(0,0,0,0.7) 0%, transparent 100%);
    z-index: 1;
}

.image {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-size: cover;
    background-position: center;
    filter: brightness(0.9);
    z-index: 0;
}

.admit-one {
    position: absolute;
    color: rgba(255,255,255,0.8);
    height: 100%;
    padding: 0 15px;
    letter-spacing: 0.15em;
    display: flex;
    text-align: center;
    justify-content: space-around;
    writing-mode: vertical-rl;
    transform: rotate(-180deg);
    font-size: 12px;
    font-weight: 600;
    z-index: 2;
}

.admit-one span {
    margin: 5px 0;
}

.left .ticket-number {
    position: absolute;
    bottom: 15px;
    right: 15px;
    padding: 5px 10px;
    color: white;
    font-weight: bold;
    background: rgba(0,0,0,0.5);
    border-radius: 4px;
    z-index: 2;
    font-size: 12px;
}

.ticket-info {
    padding: 30px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-start;
    flex-grow: 1;
    position: relative;
    z-index: 2;
    color: white;
}

.date {
    border-top: 2px solid rgba(255,255,255,0.3);
    border-bottom: 2px solid rgba(255,255,255,0.3);
    padding: 8px 0;
    font-weight: 600;
    display: flex;
    align-items: center;
    width: 100%;
    justify-content: center;
    margin: 15px 0;
    font-size: 16px;
    letter-spacing: 1px;
}

.show-name {
    font-family: "Playfair Display", serif;
    font-size: 36px;
    color: white;
    margin-bottom: 5px;
    font-weight: 700;
    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    line-height: 1.2;
}

.show-name h1 {
    margin: 0;
    padding: 0;
    font-size: inherit;
}

.time {
    padding: 10px 0;
    text-align: left;
    display: flex;
    flex-direction: column;
    gap: 5px;
    font-weight: 600;
    width: 100%;
    font-size: 16px;
}

.time p {
    display: flex;
    align-items: center;
    gap: 8px;
}

.time i {
    font-size: 18px;
}

.location {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    width: 100%;
    padding-top: 15px;
    margin-top: 15px;
    border-top: 2px solid rgba(255,255,255,0.3);
    gap: 8px;
}

.location span {
    display: flex;
    align-items: center;
    gap: 8px;
}

.location i {
    font-size: 16px;
    color: rgba(255,255,255,0.8);
}

.right {
    width: 30%;
    border-left: 1px dashed #ddd;
    position: relative;
    display: flex;
    flex-direction: column;
    padding: 25px;
    background: white;
}

.right .admit-one {
    color: rgba(0,0,0,0.3);
}

.right .right-info-container {
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    text-align: center;
}

.right .show-name {
    font-family: "Montserrat", sans-serif;
    font-size: 20px;
    margin-bottom: 15px;
    color: #333;
    text-shadow: none;
    font-weight: 700;
}

.barcode {
    height: 120px;
    width: 120px;
    margin: 20px 0;
    padding: 10px;
    background: white;
    border: 1px solid #eee;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.barcode img {
    max-height: 100%;
    max-width: 100%;
    object-fit: contain;
}

.right .ticket-number {
    color: #666;
    font-weight: bold;
    margin-top: 10px;
    font-size: 14px;
}

.watermark {
    position: absolute;
    bottom: 8px;
    right: 12px;
    font-size: 8px;
    color: rgba(0, 0, 0, 0.3);
    font-weight: 400;
    font-family: "Montserrat", sans-serif;
}

.ticket-type {
    background: #4a437e;
    color: white;
    padding: 8px 15px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 20px;
}

.organizer {
    font-size: 11px;
    margin-top: 10px;
    color: #888;
}

.ticket-count {
    font-size: 11px;
    color: #888;
    margin-top: 5px;
}

.perforation {
    position: absolute;
    left: -5px;
    top: 50%;
    transform: translateY(-50%);
    height: 80%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.perforation span {
    display: block;
    width: 10px;
    height: 10px;
    background: #f5f5f5;
    border-radius: 50%;
    border: 1px solid #ddd;
}

@media print {
    body { 
        margin: 0; 
        background: white;
    }
    .ticket { 
        box-shadow: none;
        border-radius: 0;
    }
}
"""

# Template HTML adapté aux données Laravel
TICKET_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Billet - {{ ticket.event_title }}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css"/>
</head>
<body>
    <div class="ticket">
        <div class="left">
            <div class="image" style="background-image: url('{{ ticket.event_image_url }}')"></div>
            <p class="admit-one">
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
            </p>
            <div class="ticket-number">
                <p>#{{ ticket.reference }}</p>
            </div>
            <div class="ticket-info">
                <div class="show-name">
                    <h1>{{ ticket.event_title }}</h1>
                </div>
                <div class="date">
                    <i class="far fa-calendar-alt"></i> {{ ticket.event_date_time }}
                </div>
                <div class="time">
                    <p><i class="far fa-clock"></i> {{ ticket.event_time }}</p>
                </div>
                <div class="location">
                    <span><i class="fas fa-map-marker-alt"></i> {{ ticket.event_location }}</span>
                    {% if ticket.event_address %}
                    <span>{{ ticket.event_address }}</span>
                    {% endif %}
                </div>
            </div>
        </div>
        <div class="right">
            <div class="perforation">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
                <span></span>
            </div>
            <p class="admit-one">
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
            </p>
            <div class="right-info-container">
                <div class="ticket-type">{{ ticket.ticket_type }}</div>
                <div class="show-name">
                    <h1>Billet d'entrée</h1>
                </div>
                <div class="barcode">
                    <img src="{{ ticket.qr_code }}" alt="QR code">
                </div>
                <p class="ticket-number">
                    #{{ ticket.reference }}
                </p>
                {% if ticket.organizer_name %}
                <p class="organizer">Organisé par {{ ticket.organizer_name }}</p>
                {% endif %}
                {% if ticket.current_ticket and ticket.total_tickets %}
                <p class="ticket-count">Billet {{ ticket.current_ticket }} sur {{ ticket.total_tickets }}</p>
                {% endif %}
            </div>
        </div>
        <div class="watermark">Généré le {{ ticket.generated_at }}</div>
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
    <title>Billet - {{ ticket.event_title }}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css"/>
</head>
<body>
    <div class="ticket">
        <div class="left">
            <div class="image" style="background-image: url('{{ ticket.event_image_url }}')"></div>
            <p class="admit-one">
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
            </p>
            <div class="ticket-number">
                <p>#{{ ticket.reference }}</p>
            </div>
            <div class="ticket-info">
                <div class="show-name">
                    <h1>{{ ticket.event_title }}</h1>
                </div>
                <div class="date">
                    <i class="far fa-calendar-alt"></i> {{ ticket.event_date_time }}
                </div>
                <div class="time">
                    <p><i class="far fa-clock"></i> {{ ticket.event_time }}</p>
                </div>
                <div class="location">
                    <span><i class="fas fa-map-marker-alt"></i> {{ ticket.event_location }}</span>
                    {% if ticket.event_address %}
                    <span>{{ ticket.event_address }}</span>
                    {% endif %}
                </div>
            </div>
        </div>
        <div class="right">
            <div class="perforation">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
                <span></span>
            </div>
            <p class="admit-one">
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
            </p>
            <div class="right-info-container">
                <div class="ticket-type">{{ ticket.ticket_type }}</div>
                <div class="show-name">
                    <h1>Billet d'entrée</h1>
                </div>
                <div class="barcode">
                    <img src="{{ ticket.qr_code }}" alt="QR code">
                </div>
                <p class="ticket-number">
                    #{{ ticket.reference }}
                </p>
                {% if ticket.organizer_name %}
                <p class="organizer">Organisé par {{ ticket.organizer_name }}</p>
                {% endif %}
                {% if ticket.current_ticket and ticket.total_tickets %}
                <p class="ticket-count">Billet {{ ticket.current_ticket }} sur {{ ticket.total_tickets }}</p>
                {% endif %}
            </div>
        </div>
        <div class="watermark">Généré le {{ ticket.generated_at }}</div>
    </div>
</body>
</html>
"""

def validate_ticket_data(data):
    """Valide les données du billet selon le format Laravel"""
    required_fields = [
        'event_title', 'event_date_time', 'event_location',
        'ticket_type', 'qr_code', 'reference'
    ]
    
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"Champ requis manquant: {field}")
    
    # Champs optionnels avec valeurs par défaut
    if 'event_image_url' not in data or not data['event_image_url']:
        data['event_image_url'] = "data:image/svg+xml;base64,..."  # Image par défaut
    
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
        'service': 'PDF Ticket Generator',
        'timestamp': datetime.now().isoformat(),
        'version': '4.0.0'
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
        if 'event_image_url' in ticket_data and ticket_data['event_image_url']:
            processed_image = process_image_url(ticket_data['event_image_url'])
            ticket_data['event_image_url'] = processed_image
        
        # Rendu HTML
        html_content = render_template_string(TICKET_HTML_TEMPLATE, ticket=ticket_data)
        
        # Génération PDF
        html_doc = HTML(string=html_content)
        css_doc = CSS(string=TICKET_CSS)
        
        pdf_buffer = io.BytesIO()
        html_doc.write_pdf(pdf_buffer, stylesheets=[css_doc])
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
        
        # Rendu HTML
        html_content = render_template_string(MULTIPLE_TICKETS_HTML_TEMPLATE, tickets=validated_tickets)
        
        # Génération PDF
        html_doc = HTML(string=html_content)
        css_doc = CSS(string=TICKET_CSS)
        
        pdf_buffer = io.BytesIO()
        html_doc.write_pdf(pdf_buffer, stylesheets=[css_doc])
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