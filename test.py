import requests
import json
from urllib.parse import quote  # Ajout de l'import pour l'encodage URL

# URLs du service
SINGLE_TICKET_URL = "http://localhost:5000/generate-ticket"
MULTIPLE_TICKETS_URL = "http://localhost:5000/generate-multiple-tickets"

# Données communes
EVENT_IMAGE_URL = "https://images.unsplash.com/photo-1511578314322-379afb476865"

# Modèle de billet
def create_ticket_data(ref, type_billet="VIP", prix="49 FCFA"):
    # Encoder la référence pour l'URL QR code
    encoded_ref = quote(ref)
    return {
        "event_title": "FESTIVAL DE MUSIQUE ÉLECTRONIQUE",
        "event_date_time": "Samedi 25 Août 2023 à 20h",
        "event_location": "LA GRANDE SCÈNE",
        "event_address": "123 Boulevard de l'Événement, 75000 Paris",
        "event_type": "CONCERT",
        "organizer_name": "MFUMUENTERTAINMENT",
        "ticket_price": prix,
        "ticket_reference": ref,  # On garde la référence originale pour l'affichage
        "ticket_type": type_billet,
        "qr_code_url": "https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=test",
        "event_image_url": EVENT_IMAGE_URL,
        "format": {
            "width": "180mm",
            "height": "70mm"
        }
    }

# Test billet unique
def test_single_ticket():
    print("=== Génération d'un seul billet ===")
    payload = {
        "ticket": create_ticket_data("#EVT2023-0001")
    }

    try:
        response = requests.post(SINGLE_TICKET_URL, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            with open("ticket_unique.pdf", "wb") as f:
                f.write(response.content)
            print("✅ Billet unique généré : ticket_unique.pdf")
        else:
            print("❌ Erreur:", response.text)
    except Exception as e:
        print("❌ Exception:", e)

# Test plusieurs billets
def test_multiple_tickets():
    print("\n=== Génération de plusieurs billets ===")
    tickets = [
        create_ticket_data("#EVT2023-0001", "VIP", "49 FCFA"),
        create_ticket_data("#EVT2023-0002", "Standard", "29 FCFA"),
        create_ticket_data("#EVT2023-0003", "Premium", "69 FCFA"),
        create_ticket_data("#EVT2023-0005", "VVIP", "3000 FCFA"),
        create_ticket_data("#EVT2023-0006", "GUEST", "20000 FCFA")
    ]
    payload = {
        "tickets": tickets,
        "format": {
            "width": "180mm",
            "height": "70mm"
        }
    }

    try:
        response = requests.post(MULTIPLE_TICKETS_URL, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            with open("tickets_multiples.pdf", "wb") as f:
                f.write(response.content)
            print("✅ Billets multiples générés : tickets_multiples.pdf")
        else:
            print("❌ Erreur:", response.text)
    except Exception as e:
        print("❌ Exception:", e)

if __name__ == "__main__":
    test_single_ticket()
    test_multiple_tickets()