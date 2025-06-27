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

# CSS pour le nouveau design de billet
TICKET_CSS = """
@import url("https://fonts.googleapis.com/css2?family=Staatliches&display=swap");
@import url("https://fonts.googleapis.com/css2?family=Nanum+Pen+Script&display=swap");
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
    font-family: "Staatliches", cursive;
    background: #d83565;
    color: black;
    font-size: 14px;
    letter-spacing: 0.1em;
}

.ticket {
    margin: 0 auto;
    display: flex;
    background: white;
    box-shadow: rgba(0, 0, 0, 0.3) 0px 19px 38px, rgba(0, 0, 0, 0.22) 0px 15px 12px;
    width: 210mm;
    height: 100mm;
}

.left {
    display: flex;
    width: 70%;
}

.image {
    height: 100%;
    width: 250px;
    background-size: cover;
    background-position: center;
    opacity: 0.85;
    position: relative;
}

.admit-one {
    position: absolute;
    color: darkgray;
    height: 100%;
    padding: 0 10px;
    letter-spacing: 0.15em;
    display: flex;
    text-align: center;
    justify-content: space-around;
    writing-mode: vertical-rl;
    transform: rotate(-180deg);
}

.admit-one span:nth-child(2) {
    color: white;
    font-weight: 700;
}

.left .ticket-number {
    position: absolute;
    bottom: 10px;
    right: 10px;
    padding: 5px;
    color: white;
    font-weight: bold;
}

.ticket-info {
    padding: 20px 30px;
    display: flex;
    flex-direction: column;
    text-align: center;
    justify-content: space-between;
    align-items: center;
    flex-grow: 1;
}

.date {
    border-top: 1px solid gray;
    border-bottom: 1px solid gray;
    padding: 5px 0;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: space-around;
    width: 100%;
}

.date span {
    width: 100px;
}

.date span:first-child {
    text-align: left;
}

.date span:last-child {
    text-align: right;
}

.date .event-date {
    color: #d83565;
    font-size: 20px;
}

.show-name {
    font-size: 32px;
    font-family: "Nanum Pen Script", cursive;
    color: #d83565;
}

.show-name h1 {
    font-size: 48px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #4a437e;
    margin-bottom: 10px;
}

.show-name h2 {
    font-size: 24px;
    color: #d83565;
    margin-bottom: 20px;
}

.time {
    padding: 10px 0;
    color: #4a437e;
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 10px;
    font-weight: 700;
    width: 100%;
}

.time span {
    font-weight: 400;
    color: gray;
}

.location {
    display: flex;
    justify-content: space-around;
    align-items: center;
    width: 100%;
    padding-top: 8px;
    border-top: 1px solid gray;
}

.location .separator {
    font-size: 20px;
}

.right {
    width: 30%;
    border-left: 1px dashed #404040;
    position: relative;
}

.right .admit-one {
    color: darkgray;
}

.right .admit-one span:nth-child(2) {
    color: gray;
}

.right .right-info-container {
    height: 100%;
    padding: 20px 10px 20px 35px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
}

.right .show-name h1 {
    font-size: 24px;
    margin-bottom: 10px;
}

.barcode {
    height: 120px;
    margin: 20px 0;
}

.barcode img {
    height: 100%;
    width: auto;
}

.right .ticket-number {
    color: gray;
    font-weight: bold;
    margin-top: 10px;
}

.watermark {
    position: absolute;
    bottom: 8px;
    right: 12px;
    font-size: 7px;
    color: rgba(0, 0, 0, 0.4);
    font-weight: 500;
}

@media print {
    body { 
        margin: 0; 
        background: white;
    }
    .ticket { 
        box-shadow: none;
    }
}
"""

# Template HTML pour le nouveau design
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
    <div class="ticket created-by-anniedotexe">
        <div class="left">
            <div class="image" style="background-image: url('{{ ticket.event_image_url }}')">
                <p class="admit-one">
                    <span>ADMIT ONE</span>
                    <span>ADMIT ONE</span>
                    <span>ADMIT ONE</span>
                </p>
                <div class="ticket-number">
                    <p>#{{ ticket.reference }}</p>
                </div>
            </div>
            <div class="ticket-info">
                <p class="date">
                    <span>{{ ticket.event_day }}</span>
                    <span class="event-date">{{ ticket.event_date }}</span>
                    <span>{{ ticket.event_year }}</span>
                </p>
                <div class="show-name">
                    <h1>{{ ticket.event_title }}</h1>
                    <h2>{{ ticket.artist_name }}</h2>
                </div>
                <div class="time">
                    <p>{{ ticket.event_time }} <span>TO</span> {{ ticket.event_end_time }}</p>
                    <p>DOORS <span>@</span> {{ ticket.doors_open_time }}</p>
                </div>
                <p class="location">
                    <span>{{ ticket.event_location }}</span>
                    <span class="separator"><i class="far fa-smile"></i></span>
                    <span>{{ ticket.event_city }}</span>
                </p>
            </div>
        </div>
        <div class="right">
            <p class="admit-one">
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
            </p>
            <div class="right-info-container">
                <div class="show-name">
                    <h1>{{ ticket.event_title }}</h1>
                </div>
                <div class="time">
                    <p>{{ ticket.event_time }} <span>TO</span> {{ ticket.event_end_time }}</p>
                    <p>DOORS <span>@</span> {{ ticket.doors_open_time }}</p>
                </div>
                <div class="barcode">
                    <img src="{{ ticket.qr_code }}" alt="QR code">
                </div>
                <p class="ticket-number">
                    #{{ ticket.reference }}
                </p>
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
    <title>Billets - {{ tickets[0].event_title }}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css"/>
</head>
<body>
    {% for ticket in tickets %}
    <div class="ticket created-by-anniedotexe" style="{% if not loop.first %}page-break-before: always;{% endif %}">
        <div class="left">
            <div class="image" style="background-image: url('{{ ticket.event_image_url }}')">
                <p class="admit-one">
                    <span>ADMIT ONE</span>
                    <span>ADMIT ONE</span>
                    <span>ADMIT ONE</span>
                </p>
                <div class="ticket-number">
                    <p>#{{ ticket.reference }}</p>
                </div>
            </div>
            <div class="ticket-info">
                <p class="date">
                    <span>{{ ticket.event_day }}</span>
                    <span class="event-date">{{ ticket.event_date }}</span>
                    <span>{{ ticket.event_year }}</span>
                </p>
                <div class="show-name">
                    <h1>{{ ticket.event_title }}</h1>
                    <h2>{{ ticket.artist_name }}</h2>
                </div>
                <div class="time">
                    <p>{{ ticket.event_time }} <span>TO</span> {{ ticket.event_end_time }}</p>
                    <p>DOORS <span>@</span> {{ ticket.doors_open_time }}</p>
                </div>
                <p class="location">
                    <span>{{ ticket.event_location }}</span>
                    <span class="separator"><i class="far fa-smile"></i></span>
                    <span>{{ ticket.event_city }}</span>
                </p>
            </div>
        </div>
        <div class="right">
            <p class="admit-one">
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
                <span>ADMIT ONE</span>
            </p>
            <div class="right-info-container">
                <div class="show-name">
                    <h1>{{ ticket.event_title }}</h1>
                </div>
                <div class="time">
                    <p>{{ ticket.event_time }} <span>TO</span> {{ ticket.event_end_time }}</p>
                    <p>DOORS <span>@</span> {{ ticket.doors_open_time }}</p>
                </div>
                <div class="barcode">
                    <img src="{{ ticket.qr_code }}" alt="QR code">
                </div>
                <p class="ticket-number">
                    #{{ ticket.reference }}
                </p>
            </div>
        </div>
        <div class="watermark">Généré le {{ ticket.generated_at }}</div>
    </div>
    {% endfor %}
</body>
</html>
"""

def validate_ticket_data(data):
    """Valide les données du billet selon le format Laravel"""
    required_fields = [
        'event_title', 'artist_name', 'event_day', 'event_date', 'event_year',
        'event_time', 'event_end_time', 'doors_open_time', 'event_location', 
        'event_city', 'qr_code', 'reference'
    ]
    
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"Champ requis manquant: {field}")
    
    # Champs optionnels avec valeurs par défaut
    if 'event_image_url' not in data or not data['event_image_url']:
        data['event_image_url'] = "https://media.pitchfork.com/photos/60db53e71dfc7ddc9f5086f9/1:1/w_1656,h_1656,c_limit/Olivia-Rodrigo-Sour-Prom.jpg"
    
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
        'version': '4.0.0',
        'features': ['New Ticket Design', 'Multiple Tickets', 'QR Code Support']
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
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css"/>
        </head>
        <body style="background: #f5f7fa; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh;">
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