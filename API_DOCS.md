# Documentation de l'API du service de génération de PDF

## Générer des billets PDF

Génère un ou plusieurs billets PDF au format 180x70mm (paysage).

**URL** : `/generate`

**Méthode** : `POST`

**Authentification requise** : Non (à configurer en production)

### Corps de la requête

```json
{
  "tickets": [
    {
      "event": {
        "id": 1,
        "name": "Concert de musique",
        "start_date": "2023-12-31T23:00:00",
        "location": "Salle des fêtes",
        "description": "Description de l'événement"
      },
      "ticket": {
        "id": 1,
        "name": "Place Standard",
        "price": 5000,
        "quantity": 1
      },
      "payment": {
        "id": 123,
        "matricule": "TKT123",
        "amount": 5000,
        "status": "completed",
        "created_at": "2023-12-01T10:00:00",
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890"
      },
      "index": 1,
      "total": 3,
      "qrCode": "data:image/svg+xml;base64,...",
      "eventImage": "data:image/jpeg;base64,..."
    }
  ]
}
```

### Réponse en cas de succès

**Code** : `200 OK`

**En-têtes** :
- `Content-Type: application/pdf`
- `Content-Disposition: inline; filename="tickets.pdf"`

**Corps** : Fichier PDF binaire

### Réponse en cas d'erreur

**Code** : `400 Bad Request` ou `500 Internal Server Error`

**Corps** :
```json
{
  "error": "Message d'erreur détaillé",
  "details": "Informations supplémentaires sur l'erreur (en développement)"
}
```

## Vérifier l'état du service

Vérifie que le service est opérationnel.

**URL** : `/health`

**Méthode** : `GET`

### Réponse en cas de succès

**Code** : `200 OK`

**Corps** :
```json
{
  "status": "ok"
}
```

## Exemple d'utilisation avec cURL

```bash
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "tickets": [
      {
        "event": {
          "id": 1,
          "name": "Concert de musique",
          "start_date": "2023-12-31T23:00:00",
          "location": "Salle des fêtes",
          "description": "Description de l\'événement"
        },
        "ticket": {
          "id": 1,
          "name": "Place Standard",
          "price": 5000,
          "quantity": 1
        },
        "payment": {
          "id": 123,
          "matricule": "TKT123",
          "amount": 5000,
          "status": "completed",
          "created_at": "2023-12-01T10:00:00",
          "name": "John Doe",
          "email": "john@example.com",
          "phone": "+1234567890"
        },
        "index": 1,
        "total": 1,
        "qrCode": "data:image/svg+xml;base64,PHN2...",
        "eventImage": "data:image/jpeg;base64,/9j/4..."
      }
    ]
  }' \
  --output billets.pdf
```

## Codes d'erreur

| Code | Signification |
|------|---------------|
| 400  | Requête invalide |
| 500  | Erreur interne du serveur |
| 503  | Service indisponible |

## Sécurité

En production, il est recommandé de :
1. Activer l'authentification entre les services
2. Configurer HTTPS
3. Mettre en place une limitation de débit (rate limiting)
4. Mettre en place des en-têtes de sécurité (CORS, etc.)
