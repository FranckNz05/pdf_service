# PDF Generation Service

Un service web simple pour générer des PDF à partir de modèles HTML en utilisant Flask et WeasyPrint.

## Fonctionnalités

- Génération de PDF à partir de modèles HTML
- API RESTful simple
- Gestion des erreurs complète
- Prêt pour le déploiement sur Render

## Prérequis

- Python 3.9+
- pip

## Installation locale

1. Clonez le dépôt :
   ```bash
   git clone <votre-depot>
   cd pdf_service
   ```

2. Créez et activez un environnement virtuel :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Sur Windows: venv\Scripts\activate
   ```

3. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

4. Créez un fichier `.env` à la racine du projet :
   ```env
   FLASK_APP=app.py
   FLASK_ENV=development
   ```

5. Lancez l'application :
   ```bash
   flask run
   ```

## API Endpoints

- `GET /` - Vérifie que le service fonctionne
- `POST /generate-ticket` - Génère un PDF à partir des données fournies

### Exemple de requête

```bash
curl -X POST http://localhost:5000/generate-ticket \
  -H "Content-Type: application/json" \
  -d '{"title":"Mon Ticket", "content":"Contenu du ticket"}'
```

## Déploiement sur Render

1. Créez un nouveau service Web sur Render
2. Liez votre dépôt GitHub
3. Configurez les paramètres suivants :
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Définissez les variables d'environnement si nécessaire
5. Déployez !

## Structure du projet

```
.
├── app.py              # Application principale
├── requirements.txt    # Dépendances Python
├── runtime.txt         # Version de Python
├── Procfile           # Configuration pour le déploiement
├── wsgi.py            # Point d'entrée WSGI
├── templates/         # Dossier pour les modèles HTML
│   └── ticket_template.html
└── README.md          # Ce fichier
```

## Licence

MIT
