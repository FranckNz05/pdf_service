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

# CSS amélioré pour le design de billet (180mm x 70mm) - Version corrigée
TICKET_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@400;600;700;800&display=swap');

@page {
    size: 180mm 70mm;
    margin: 0;
    padding: 0;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 0;
    font-family: 'Inter', sans-serif;
    background: #ffffff;
    width: 180mm;
    height: 70mm;
    overflow: hidden;
}

.ticket-container {
    width: 180mm;
    height: 70mm;
    position: relative;
    background: #ffffff;
    overflow: hidden;
}

.ticket {
    display: flex;
    height: 100%;
    width: 100%;
    position: relative;
    background: white;
    overflow: hidden;
}

/* Ligne de découpe perforée */
.ticket::before {
    content: '';
    position: absolute;
    right: 45mm;
    top: 0;
    height: 100%;
    width: 2px;
    background: repeating-linear-gradient(
        to bottom,
        #ddd 0px,
        #ddd 4px,
        transparent 4px,
        transparent 8px
    );
    z-index: 10;
}

/* Cercles de perforation */
.ticket::after {
    content: '';
    position: absolute;
    right: 44mm;
    top: 50%;
    transform: translateY(-50%);
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #ddd;
    box-shadow: 
        0 -25mm 0 #ddd,
        0 -20mm 0 #ddd,
        0 -15mm 0 #ddd,
        0 -10mm 0 #ddd,
        0 -5mm 0 #ddd,
        0 5mm 0 #ddd,
        0 10mm 0 #ddd,
        0 15mm 0 #ddd,
        0 20mm 0 #ddd,
        0 25mm 0 #ddd;
    z-index: 11;
}

.ticket-main {
    flex: 1;
    display: flex;
    position: relative;
    background: white;
    width: calc(180mm - 45mm);
    height: 100%;
}

.ticket-left {
    width: 50mm;
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.event-image-container {
    width: 100%;
    height: 100%;
    position: relative;
    overflow: hidden;
}

.event-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center;
}

.image-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
        135deg, 
        rgba(102, 126, 234, 0.1) 0%, 
        rgba(118, 75, 162, 0.1) 100%
    );
}

.price-badge {
    position: absolute;
    top: 8mm;
    left: 0;
    background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
    color: #1a202c;
    padding: 8px 16px 8px 12px;
    font-size: 14px;
    font-weight: 800;
    border-radius: 0 25px 25px 0;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    z-index: 5;
    clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 50%, calc(100% - 8px) 100%, 0 100%);
}

.ticket-center {
    flex: 1;
    padding: 12mm 10mm;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: white;
    position: relative;
}

.event-header {
    margin-bottom: 8mm;
}

.event-title {
    font-family: 'Playfair Display', serif;
    font-size: 22px;
    font-weight: 700;
    color: #1a202c;
    line-height: 1.2;
    margin: 0 0 6px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    /* Troncature pour titres longs */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    max-height: 2.4em;
}

.event-subtitle {
    font-size: 12px;
    color: #64748b;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.ticket-details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6mm;
    margin-bottom: 6mm;
}

.detail-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.detail-label {
    font-size: 10px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.detail-value {
    font-size: 13px;
    font-weight: 600;
    color: #1a202c;
    line-height: 1.4;
    /* Troncature pour valeurs longues */
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}

.detail-icon {
    width: 14px;
    height: 14px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border-radius: 4px;
    font-size: 9px;
    flex-shrink: 0;
}

.organizer-info {
    padding: 6mm 0 0 0;
    border-top: 1px solid #e2e8f0;
    text-align: center;
}

.organizer-label {
    font-size: 10px;
    color: #64748b;
    font-weight: 500;
    margin-bottom: 4px;
}

.organizer-name {
    font-size: 12px;
    font-weight: 700;
    color: #1a202c;
    /* Troncature pour nom organisateur */
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.ticket-stub {
    width: 45mm;
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    padding: 10mm;
}

.ticket-type-badge {
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
    color: #1a202c;
    padding: 6px 16px;
    border-radius: 0 0 12px 12px;
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 40mm;
}

.qr-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    margin-top: 8mm;
}

.qr-label {
    color: #94a3b8;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    text-align: center;
    line-height: 1.3;
}

.qr-code-container {
    width: 60px;
    height: 60px;
    background: white;
    padding: 6px;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
}

.qr-code-container img {
    width: 100%;
    height: 100%;
    border-radius: 6px;
}

.ticket-reference {
    color: #64748b;
    font-size: 9px;
    font-family: 'Courier New', monospace;
    text-align: center;
    font-weight: 500;
    line-height: 1.3;
    margin-top: 6px;
}

.ticket-reference-label {
    font-size: 8px;
    color: #475569;
    margin-bottom: 3px;
    font-weight: 600;
}

/* Responsive adjustments pour les petits billets */
@media print {
    .ticket-container {
        animation: none;
    }
    
    body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
}

/* Amélioration de la lisibilité sur fond sombre */
.ticket-stub * {
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}

/* Gestion des très longs textes */
.long-text {
    word-break: break-word;
    hyphens: auto;
}
"""

# Template HTML amélioré avec meilleure structure
TICKET_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Billet - {{ ticket.event_title }}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="ticket-container">
        <div class="ticket">
            <div class="ticket-main">
                <div class="ticket-left">
                    {% if ticket.ticket_price %}
                    <div class="price-badge">
                        {{ ticket.ticket_price }}
                    </div>
                    {% endif %}
                    <div class="event-image-container">
                        <img class="event-image" src="{{ ticket.event_image_url }}" alt="{{ ticket.event_title }}">
                        <div class="image-overlay"></div>
                    </div>
                </div>

                <div class="ticket-center">
                    <div class="event-header">
                        <h1 class="event-title">{{ ticket.event_title }}</h1>
                        <div class="event-subtitle">Billet d'entrée</div>
                    </div>

                    <div class="ticket-details">
                        <div class="detail-group">
                            <div class="detail-label">
                                <span class="detail-icon">
                                    <i class="fas fa-calendar"></i>
                                </span>
                                Date & Heure
                            </div>
                            <div class="detail-value">{{ ticket.event_date_time }}</div>
                        </div>

                        <div class="detail-group">
                            <div class="detail-label">
                                <span class="detail-icon">
                                    <i class="fas fa-map-marker-alt"></i>
                                </span>
                                Lieu
                            </div>
                            <div class="detail-value long-text">
                                {{ ticket.event_location }}
                                {% if ticket.event_address %}
                                <br><span style="font-size: 11px; color: #64748b;">{{ ticket.event_address }}</span>
                                {% endif %}
                            </div>
                        </div>
                    </div>

                    <div class="organizer-info">
                        <div class="organizer-label">Organisé par</div>
                        <div class="organizer-name">{{ ticket.organizer_name }}</div>
                    </div>
                </div>
            </div>

            <div class="ticket-stub">
                <div class="ticket-type-badge">
                    {{ ticket.ticket_type }}
                </div>

                <div class="qr-section">
                    <div class="qr-label">
                        Scanner pour<br>validation
                    </div>

                    <div class="qr-code-container">
                        <img src="{{ ticket.qr_code }}" alt="QR Code de validation">
                    </div>

                    <div class="ticket-reference">
                        <div class="ticket-reference-label">RÉFÉRENCE</div>
                        {{ ticket.reference }}
                        {% if ticket.current_ticket and ticket.total_tickets %}
                        <br>{{ ticket.current_ticket }}/{{ ticket.total_tickets }}
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Template pour tickets multiples avec page break
MULTIPLE_TICKETS_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Billets - {{ tickets[0].event_title }}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .page-break {
            page-break-before: always;
        }
    </style>
</head>
<body>
    {% for ticket in tickets %}
    <div class="ticket-container{% if not loop.first %} page-break{% endif %}">
        <div class="ticket">
            <div class="ticket-main">
                <div class="ticket-left">
                    {% if ticket.ticket_price %}
                    <div class="price-badge">
                        {{ ticket.ticket_price }}
                    </div>
                    {% endif %}
                    <div class="event-image-container">
                        <img class="event-image" src="{{ ticket.event_image_url }}" alt="{{ ticket.event_title }}">
                        <div class="image-overlay"></div>
                    </div>
                </div>

                <div class="ticket-center">
                    <div class="event-header">
                        <h1 class="event-title">{{ ticket.event_title }}</h1>
                        <div class="event-subtitle">Billet d'entrée</div>
                    </div>

                    <div class="ticket-details">
                        <div class="detail-group">
                            <div class="detail-label">
                                <span class="detail-icon">
                                    <i class="fas fa-calendar"></i>
                                </span>
                                Date & Heure
                            </div>
                            <div class="detail-value">{{ ticket.event_date_time }}</div>
                        </div>

                        <div class="detail-group">
                            <div class="detail-label">
                                <span class="detail-icon">
                                    <i class="fas fa-map-marker-alt"></i>
                                </span>
                                Lieu
                            </div>
                            <div class="detail-value long-text">
                                {{ ticket.event_location }}
                                {% if ticket.event_address %}
                                <br><span style="font-size: 11px; color: #64748b;">{{ ticket.event_address }}</span>
                                {% endif %}
                            </div>
                        </div>
                    </div>

                    <div class="organizer-info">
                        <div class="organizer-label">Organisé par</div>
                        <div class="organizer-name">{{ ticket.organizer_name }}</div>
                    </div>
                </div>
            </div>

            <div class="ticket-stub">
                <div class="ticket-type-badge">
                    {{ ticket.ticket_type }}
                </div>

                <div class="qr-section">
                    <div class="qr-label">
                        Scanner pour<br>validation
                    </div>

                    <div class="qr-code-container">
                        <img src="{{ ticket.qr_code }}" alt="QR Code de validation">
                    </div>

                    <div class="ticket-reference">
                        <div class="ticket-reference-label">RÉFÉRENCE</div>
                        {{ ticket.reference }}
                        {% if ticket.current_ticket and ticket.total_tickets %}
                        <br>{{ ticket.current_ticket }}/{{ ticket.total_tickets }}
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
    {% endfor %}
</body>
</html>
"""

def validate_ticket_data(data):
    """Valide les données du billet"""
    required_fields = [
        'event_title', 'event_date_time', 'event_location',
        'ticket_type', 'qr_code', 'reference'
    ]
    
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"Champ requis manquant: {field}")
    
    # Champs optionnels avec valeurs par défaut
    if 'event_image_url' not in data or not data['event_image_url']:
        # Image SVG par défaut plus élégante
        data['event_image_url'] = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8ZGVmcz4KICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ3JhZCIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+CiAgICAgIDxzdG9wIG9mZnNldD0iMCUiIHN0b3AtY29sb3I9IiM2NjdlZWEiLz4KICAgICAgPHN0b3Agb2Zmc2V0PSIxMDAlIiBzdG9wLWNvbG9yPSIjNzY0YmEyIi8+CiAgICA8L2xpbmVhckdyYWRpZW50PgogIDwvZGVmcz4KICA8cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0idXJsKCNncmFkKSIvPgogIDx0ZXh0IHg9IjIwMCIgeT0iMTUwIiBmb250LWZhbWlseT0iSW50ZXIsIEFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjI4IiBmb250LXdlaWdodD0iNjAwIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSI+w4lWw4lORU1FTlQ8L3RleHQ+Cjwvc3ZnPg=="
    
    if 'organizer_name' not in data:
        data['organizer_name'] = "Organisateur"
    
    if 'ticket_price' not in data:
        data['ticket_price'] = None
    
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
            
        # Si c'est une URL HTTP/HTTPS, essayer de la télécharger
        if image_url.startswith(('http://', 'https://')):
            try:
                response = requests.get(image_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                
                content_type = response.headers.get('content-type', '')
                if 'image' not in content_type:
                    logger.warning(f"URL ne semble pas être une image: {content_type}")
                    return None
                
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                return f"data:{content_type};base64,{image_base64}"
                
            except Exception as e:
                logger.warning(f"Impossible de télécharger l'image: {e}")
                return None
        
        return None
        
    except Exception as e:
        logger.warning(f"Erreur traitement image URL: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de santé du service"""
    return jsonify({
        'status': 'healthy',
        'service': 'PDF Ticket Generator Pro',
        'timestamp': datetime.now().isoformat(),
        'version': '5.1.0',
        'ticket_size': '180mm x 70mm'
    })

@app.route('/generate-ticket', methods=['POST'])
def generate_single_ticket():
    """Génère un billet unique au format 180mm x 70mm"""
    try:
        data = request.get_json()
        
        if not data or 'ticket' not in data:
            return jsonify({'error': 'Données de billet requises'}), 400
            
        ticket_data = validate_ticket_data(data['ticket'])
        
        # Traitement de l'image
        if 'event_image_url' in ticket_data and ticket_data['event_image_url']:
            processed_image = process_image_url(ticket_data['event_image_url'])
            if processed_image:
                ticket_data['event_image_url'] = processed_image
        
        # Rendu HTML
        html_content = render_template_string(TICKET_HTML_TEMPLATE, ticket=ticket_data)
        
        # Génération PDF avec options optimisées
        html_doc = HTML(string=html_content, base_url=request.url_root)
        css_doc = CSS(string=TICKET_CSS)
        
        pdf_buffer = io.BytesIO()
        html_doc.write_pdf(
            pdf_buffer, 
            stylesheets=[css_doc]
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
        logger.error(f"Erreur génération billet: {str(e)}", exc_info=True)
        return jsonify({'error': 'Erreur interne du serveur', 'details': str(e)}), 500

@app.route('/generate-multiple-tickets', methods=['POST'])
def generate_multiple_tickets():
    """Génère plusieurs billets en un seul PDF"""
    try:
        data = request.get_json()
        
        if not data or 'tickets' not in data or not isinstance(data['tickets'], list):
            return jsonify({'error': 'Liste de billets requise'}), 400
            
        if len(data['tickets']) == 0:
            return jsonify({'error': 'Au moins un billet requis'}), 400
            
        if len(data['tickets']) > 50:
            return jsonify({'error': 'Maximum 50 billets par requête'}), 400
        
        # Validation de tous les billets
        validated_tickets = []
        for i, ticket in enumerate(data['tickets']):
            try:
                validated_ticket = validate_ticket_data(ticket)
                # Ajouter numérotation automatique si pas présente
                if 'current_ticket' not in validated_ticket:
                    validated_ticket['current_ticket'] = i + 1
                if 'total_tickets' not in validated_ticket:
                    validated_ticket['total_tickets'] = len(data['tickets'])
                    
                if 'event_image_url' in validated_ticket and validated_ticket['event_image_url']:
                    processed_image = process_image_url(validated_ticket['event_image_url'])
                    if processed_image:
                        validated_ticket['event_image_url'] = processed_image
                validated_tickets.append(validated_ticket)
            except ValueError as e:
                return jsonify({'error': f'Erreur billet {i+1}: {str(e)}'}), 400
        
        # Rendu HTML
        html_content = render_template_string(MULTIPLE_TICKETS_HTML_TEMPLATE, tickets=validated_tickets)
        
        # Génération PDF
        html_doc = HTML(string=html_content, base_url=request.url_root)
        css_doc = CSS(string=TICKET_CSS)
        
        pdf_buffer = io.BytesIO()
        html_doc.write_pdf(
            pdf_buffer, 
            stylesheets=[css_doc]
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
        logger.error(f"Erreur génération billets multiples: {str(e)}", exc_info=True)
        return jsonify({'error': 'Erreur interne du serveur', 'details': str(e)}), 500

@app.route('/preview-ticket', methods=['POST'])
def preview_ticket():
    """Génère un aperçu HTML du billet (pour tests)"""
    try:
        data = request.get_json()
        
        if not data or 'ticket' not in data:
            return jsonify({'error': 'Données de billet requises'}), 400
            
        ticket_data = validate_ticket_data(data['ticket'])
        
        # Traitement de l'image
        if 'event_image_url' in ticket_data and ticket_data['event_image_url']:
            processed_image = process_image_url(ticket_data['event_image_url'])
            if processed_image:
                ticket_data['event_image_url'] = processed_image
        
        # Rendu HTML avec CSS intégré
        html_content = f"""
        <style>{TICKET_CSS}</style>
        {render_template_string(TICKET_HTML_TEMPLATE, ticket=ticket_data)}
        """
        
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        logger.error(f"Erreur aperçu billet: {str(e)}", exc_info=True)
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
    logger.error(f"Erreur non gérée: {str(e)}", exc_info=True)
    return jsonify({
        'error': 'Erreur interne du serveur',
        'message': str(e) if app.debug else 'Une erreur est survenue'
    }), 500

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    )