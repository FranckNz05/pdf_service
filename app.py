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
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Playfair+Display:wght@700&display=swap');

    body {
      background: #f5f5f5;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      font-family: 'Poppins', sans-serif;
      padding: 10px;
    }

    .ticket-container {
      width: 900px;
      height: 70mm;
      position: relative;
      box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
      overflow: hidden;
    }

    .ticket {
      display: flex;
      height: 100%;
      background: white;
      position: relative;
    }

    .ticket::after {
      content: '';
      position: absolute;
      left: 75%;
      height: 100%;
      width: 1px;
      background: repeating-linear-gradient(to bottom,
        transparent,
        transparent 10px,
        rgba(255,255,255,0.5) 10px,
        rgba(255,255,255,0.5) 20px);
      z-index: 2;
    }

    .ticket-left {
      width: 45%;
      position: relative;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .event-image-container {
      flex-grow: 1;
      overflow: hidden;
      position: relative;
      margin-left: -15%;
      width: 115%;
    }

    .event-image-container::after {
      content: '';
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      width: 30%;
      background: linear-gradient(to right, rgba(248, 249, 250, 0), rgba(248, 249, 250, 1));
    }

    .event-image {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .price-tag {
      background: #ffd700;
      color: #0f1a3d;
      padding: 8px 25px;
      border-radius: 0 50px 50px 0;
      font-size: 18px;
      font-weight: 700;
      margin-left: -20px;
      margin-top: 20px;
      width: fit-content;
      box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2);
      position: absolute;
      top: 0;
      z-index: 2;
    }

    .ticket-center {
      width: 60%;
      padding: 20px 15px;
      display: flex;
      flex-direction: column;
      background: #f8f9fa;
      position: relative;
      align-items: center;
    }

    .ticket-right {
      width: 20%;
      background: #0f1a3d;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-start;
      position: relative;
      padding: 20px;
    }

    .ticket-type {
      background: #ffd700;
      color: #0f1a3d;
      padding: 8px 15px;
      border-radius: 0 0 10px 10px;
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 9px;
      text-transform: uppercase;
      letter-spacing: 3px;
      width: 70%;
      text-align: center;
      position: absolute;
      top: 0px;
      box-shadow: 0 -2px 5px rgba(0,0,0,0.1);
    }

    .event-title-container {
      width: 100%;
      z-index: 2;
      margin-bottom: 20px;
      text-align: center;
    }

    .event-title {
      font-family: 'Playfair Display', serif;
      font-size: 26px;
      font-weight: 700;
      color: #0f1a3d;
      line-height: 1.2;
      text-transform: uppercase;
      text-shadow: 1px 2px 3px rgba(187, 184, 184, 0.5);
      margin: 0;
      white-space: normal;
      word-wrap: break-word;
      padding: 0 10px;
    }

    .ticket-info {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 15px;
      width: 100%;
      padding: 0 10px;
    }

    .info-group {
      display: flex;
      flex-direction: column;
    }

    .info-header {
      display: flex;
      align-items: center;
      margin-bottom: 5px;
    }

    .info-icon {
      width: 20px;
      height: 20px;
      background: #0f1a3d;
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 8px;
      font-size: 10px;
    }

    .info-label {
      font-size: 12px;
      font-weight: 700;
      color: #495057;
      letter-spacing: 0.5px;
    }

    .info-value {
      font-size: 13px;
      color: #212529;
      font-weight: 500;
      padding-left: 28px;
    }

    .info-organisateur {
        text-align: center;
        padding-top: 30px;
    }

    .ticket-qr {
      width: 80px;
      height: 80px;
      background: white;
      padding: 5px;
      border-radius: 6px;
      margin-bottom: 10px;
      margin-top: 25px;
      box-shadow: 0 3px 8px rgba(0, 0, 0, 0.2);
    }

    .ticket-qr img {
      width: 100%;
      height: 100%;
    }

    .qr-label {
      color: white;
      font-size: 12px;
      text-align: center;
      margin-bottom: 10px;
      font-weight: 600;
    }

    .ticket-number {
      font-size: 10px;
      color: rgba(255, 255, 255, 0.8);
      text-align: center;
      font-family: monospace;
      margin-top: 5px;
    }

    .ticket-footer {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 8px;
      text-align: center;
      font-size: 10px;
      color: #6c757d;
      background: #f8f9fa;
      border-top: 1px solid #dee2e6;
      font-weight: 500;
      z-index: 2;
    }
"""

# Template HTML adapté aux données Laravel
TICKET_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ticket - MOKILIEVENT</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
  <div class="ticket-container">
    <div class="ticket">
      <div class="ticket-left">
        <div class="price-tag">
          {{ number_format($ticket->pivot->unit_price, 0, ',', ' ') }} FCFA
        </div>
        <div class="event-image-container">
          @if($event->image)
            <img class="event-image" src="{{ public_path('storage/' . $event->image) }}" alt="{{ $event->title }}">
          @else
            <img class="event-image" src="https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1740&q=80" alt="Événement">
          @endif
        </div>
      </div>

      <div class="ticket-center">
        <div class="event-title-container">
          <h1 class="event-title">{{ strtoupper($event->title) }}</h1>
        </div>

        <div class="ticket-info">
          <div class="info-group">
            <div class="info-header">
              <div class="info-icon">
                <i class="fas fa-calendar-alt"></i>
              </div>
              <span class="info-label">DATE & HEURE</span>
            </div>
            <span class="info-value">{{ $event->start_date->format('d M Y') }}</span>
            <span class="info-value">{{ $event->start_date->format('H:i') }}-{{ $event->end_date->format('H:i') }}</span>
          </div>

          <div class="info-group">
            <div class="info-header">
              <div class="info-icon">
                <i class="fas fa-map-marker-alt"></i>
              </div>
              <span class="info-label">LIEU</span>
            </div>
            <span class="info-value">{{ $event->lieu ?? 'Lieu non spécifié' }}</span>
            <span class="info-value">{{ $event->ville }}, {{ $event->adresse }}, {{ $event->pays }}</span>
          </div>
        </div>
        <div class="info-organisateur">
            <span class="info-value">Organisé par : <b>{{ $event->organizer->company_name ?? 'Organisateur non spécifié' }}</b></span>
        </div>
      </div>

      <div class="ticket-right">
        <div class="ticket-type">
          {{ strtoupper($ticket->nom) }}
        </div>

        <div class="qr-label">SCANNEZ CE QR CODE</div>

        <div class="ticket-qr">
          @if($payment->qr_code)
            <img src="{{ public_path('storage/' . $payment->qr_code) }}" alt="QR Code">
          @else
            <img src="{{ $qrCode }}" alt="QR Code">
          @endif
        </div>

        <div class="ticket-number">
          RÉF: {{ $payment->matricule }}{{ isset($ticketIndex) ? '-'.$ticketIndex : '' }}
        </div>
      </div>

      <div class="ticket-footer">
        Info Line : {{ $event->organizer->phone_primary ?? '+000 00 00 00 00' }} {{ $event->organizer->phone_secondary ? '/ ' . $event->organizer->phone_secondary : '' }} | Billet valable pour une personne • Non remboursable | MOKILIEVENT
      </div>
    </div>
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
  <title>Ticket - MOKILIEVENT</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
  <div class="ticket-container">
    <div class="ticket">
      <div class="ticket-left">
        <div class="price-tag">
          {{ number_format($ticket->pivot->unit_price, 0, ',', ' ') }} FCFA
        </div>
        <div class="event-image-container">
          @if($event->image)
            <img class="event-image" src="{{ public_path('storage/' . $event->image) }}" alt="{{ $event->title }}">
          @else
            <img class="event-image" src="https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1740&q=80" alt="Événement">
          @endif
        </div>
      </div>

      <div class="ticket-center">
        <div class="event-title-container">
          <h1 class="event-title">{{ strtoupper($event->title) }}</h1>
        </div>

        <div class="ticket-info">
          <div class="info-group">
            <div class="info-header">
              <div class="info-icon">
                <i class="fas fa-calendar-alt"></i>
              </div>
              <span class="info-label">DATE & HEURE</span>
            </div>
            <span class="info-value">{{ $event->start_date->format('d M Y') }}</span>
            <span class="info-value">{{ $event->start_date->format('H:i') }}-{{ $event->end_date->format('H:i') }}</span>
          </div>

          <div class="info-group">
            <div class="info-header">
              <div class="info-icon">
                <i class="fas fa-map-marker-alt"></i>
              </div>
              <span class="info-label">LIEU</span>
            </div>
            <span class="info-value">{{ $event->lieu ?? 'Lieu non spécifié' }}</span>
            <span class="info-value">{{ $event->ville }}, {{ $event->adresse }}, {{ $event->pays }}</span>
          </div>
        </div>
        <div class="info-organisateur">
            <span class="info-value">Organisé par : <b>{{ $event->organizer->company_name ?? 'Organisateur non spécifié' }}</b></span>
        </div>
      </div>

      <div class="ticket-right">
        <div class="ticket-type">
          {{ strtoupper($ticket->nom) }}
        </div>

        <div class="qr-label">SCANNEZ CE QR CODE</div>

        <div class="ticket-qr">
          @if($payment->qr_code)
            <img src="{{ public_path('storage/' . $payment->qr_code) }}" alt="QR Code">
          @else
            <img src="{{ $qrCode }}" alt="QR Code">
          @endif
        </div>

        <div class="ticket-number">
          RÉF: {{ $payment->matricule }}{{ isset($ticketIndex) ? '-'.$ticketIndex : '' }}
        </div>
      </div>

      <div class="ticket-footer">
        Info Line : {{ $event->organizer->phone_primary ?? '+000 00 00 00 00' }} {{ $event->organizer->phone_secondary ? '/ ' . $event->organizer->phone_secondary : '' }} | Billet valable pour une personne • Non remboursable | MOKILIEVENT
      </div>
    </div>
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