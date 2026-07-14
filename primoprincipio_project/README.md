# Primo Principio - Frontend + Backend Project

Repository unico che contiene sia la parte front-end sia la parte back-end della prova tecnica, sviluppate nello stesso progetto Django ma organizzate per responsabilità diverse.

La struttura implementa:
- **Problema 1**: REST API stateless in Django REST Framework per la simulazione degli eventi e dell'evoluzione di `X` nel tempo.[cite:513]
- **Problema 2**: esecuzione batch multi-giornaliera del modello Oidio, salvataggio degli snapshot degli eventi in database PostgreSQL esterno e ricostruzione delle serie temporali di `X` per ciascun evento.[cite:513]
- **Frontend**: pagine HTML Django per mappa e modello, integrate nello stesso progetto ma separate logicamente dagli endpoint API.

## Struttura del progetto

La struttura del repository è la seguente:

└── primoprincipio_project
    ├── app
    │   ├── templates
    │   ├── __init__.py
    │   ├── degree_days.py
    │   ├── openmeteo.py
    │   ├── risk.py
    │   ├── tests.py
    │   └── views.py
    ├── config
    │   ├── __init__.py
    │   ├── asgi.py
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    ├── simulation
    │   ├── migrations
    │   │   ├── __init__.py
    │   │   └── 0001_initial.py
    │   ├── test
    │   │   ├── test_problem1_api.py
    │   │   ├── test_problem2_api.py
    │   │   └── test_reconstruction.py
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── models.py
    │   ├── services.py
    │   ├── tests.py
    │   ├── urls.py
    │   └── views.py
    ├── static
    │   └── css
    │       └── style.css
    ├── templates
    │   ├── dashboard.html
    │   ├── head.html
    │   ├── map.html
    │   └── model.html
    ├── .env
    ├── docker-compose.yml
    ├── Dockerfile
    ├── manage.py
    ├── README.md
    └── requirements.txt

## Requisiti

Per eseguire il progetto in locale senza container servono:
- Python 3.11+
- pip
- PostgreSQL, se si vuole usare il setup del Problema 2 con DB esterno
- virtual environment consigliato (`venv`)

Per l'esecuzione containerizzata servono:
- Docker
- Docker Compose

## Setup ambiente locale

### 1. Clonare il repository

```bash
git clone <URL_DEL_REPOSITORY>
cd <NOME_REPOSITORY>
```

### 2. Creare e attivare un virtual environment

Su macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Su Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Installare le dipendenze

```bash
pip install -r requirements.txt
```

### 4. Configurare le variabili d'ambiente

Esempio minimo per sviluppo locale con SQLite:

```bash
export DJANGO_SECRET_KEY=dev-secret-key
export DEBUG=1
export ALLOWED_HOSTS=*
export DB_ENGINE=sqlite
export GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY
```

Esempio per sviluppo locale con PostgreSQL:

```bash
export DJANGO_SECRET_KEY=dev-secret-key
export DEBUG=1
export ALLOWED_HOSTS=*
export DB_ENGINE=postgres
export POSTGRES_DB=primoprincipio
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY
```

Se si desidera usare gli alert email, vanno impostate anche queste variabili:

```bash
export EMAIL_HOST=sandbox.smtp.mailtrap.io
export EMAIL_PORT=2525
export EMAIL_HOST_USER=<USERNAME>
export EMAIL_HOST_PASSWORD=<PASSWORD>
export EMAIL_USE_TLS=1
export DEFAULT_FROM_EMAIL=assistenza@primoprincipio.it
```

### 5. Migrazioni database

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Avvio del server di sviluppo

```bash
python manage.py runserver
```

A questo punto il progetto sarà disponibile su:

- Home / mappa: `http://127.0.0.1:8000/`
- Pagina modello: `http://127.0.0.1:8000/model/`
- Admin Django: `http://127.0.0.1:8000/admin/`

## Setup con Docker

La consegna richiede che il backend sia containerizzabile e che il database del Problema 2 sia esterno al container Django, usando PostgreSQL come servizio separato.[cite:513]

### 1. Build e avvio ambiente

```bash
docker compose up --build
```

Questo comando:
- costruisce l'immagine del backend Django dal `Dockerfile`;
- avvia un container `web` per l'applicazione;
- avvia un container `db` con immagine ufficiale PostgreSQL.

### 2. Eseguire le migrazioni nel container

In un secondo terminale:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

### 3. Aprire l'applicazione

- Home / mappa: `http://127.0.0.1:8000/`
- Pagina modello: `http://127.0.0.1:8000/model/`
- Admin Django: `http://127.0.0.1:8000/admin/`

### 4. Arrestare l'ambiente

```bash
docker compose down
```

Per eliminare anche il volume del database:

```bash
docker compose down -v
```

## Endpoint principali

### Problema 1 - Simulazione singola

`POST /api/simulation/`

Input JSON minimo:

```json
{
  "doy": 126,
  "temperature": 15.94,
  "bagnatura": 1,
  "humidity": 97.25,
  "rain": 0.0,
  "events": []
}
```

Output atteso:

```json
{
  "doy": 126,
  "events": [
    {
      "index": 0,
      "X": 0.0
    }
  ]
}
```

L'API è progettata in modo stateless: lo stato degli eventi viene passato in input e restituito in output a ogni chiamata, senza dipendere da memoria implicita lato server.[cite:513]

### Problema 2 - Batch Oidio

`POST /api/oidio-batch/`

Input JSON di esempio:

```json
{
  "events": [{"index": 0, "X": 0.0}],
  "days": [
    {"doy": 275, "temperature": 30, "bagnatura": 0, "humidity": 32, "rain": 0},
    {"doy": 276, "temperature": 28, "bagnatura": 1, "humidity": 90, "rain": 0},
    {"doy": 277, "temperature": 27, "bagnatura": 1, "humidity": 59, "rain": 22}
  ]
}
```

Output sintetico:

```json
{
  "run_id": 1,
  "outputs": [...],
  "degree_days": [...],
  "risk": {
    "level": "medio",
    "color": "yellow",
    "action": "SVEGLIATI"
  },
  "threshold": 820.0,
  "alerts_triggered": []
}
```

Per ogni risposta giornaliera del batch, il sistema salva gli snapshot in PostgreSQL in modo da poter ricostruire nel tempo la serie di valori `X` di ciascun evento.[cite:513]

### Alert API

- `GET /api/alerts/`
- `POST /api/alerts/`
- `PATCH /api/alerts/`
- `DELETE /api/alerts/`
- `GET /api/alerts/list/`

## Come eseguire i test

La traccia richiede test automatici per verificare creazione eventi, monotonicità di `X`, limite superiore `X <= 1` e corretta gestione delle iterazioni successive.[cite:513]

Eseguire tutti i test:

```bash
python manage.py test
```

Eseguire solo i test dell'app `simulation`:

```bash
python manage.py test simulation
```

Con Docker:

```bash
docker compose exec web python manage.py test
docker compose exec web python manage.py test simulation
```

## Note implementative

### Problema 1

La logica è stata isolata in `simulation/services.py` per separare l'elaborazione della simulazione dalle view HTTP. Questo rende l'API più testabile e permette di riutilizzare la stessa black-box logica anche nel Problema 2.

### Problema 2

Il batch Oidio usa il Problema 1 come black-box applicativa: per ciascun giorno invia lo stato corrente degli eventi al servizio di simulazione, riceve in uscita il nuovo stato e salva nel DB gli snapshot risultanti.[cite:513]

### Frontend nello stesso progetto

Frontend e backend sono contenuti nello stesso progetto Django, ma separati logicamente:
- le pagine HTML (`map`, `model`) sono viste di presentazione;
- gli endpoint `/api/...` espongono la parte REST;
- la logica del dominio è isolata nei service layer.

## Troubleshooting rapido

### Errore di connessione al database

Verificare:
- che PostgreSQL sia in esecuzione;
- che `DB_ENGINE=postgres` sia impostato;
- che `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` siano corretti.

### La root `/` non risponde

Verificare che `config/urls.py` includa `simulation.urls` e che `simulation/urls.py` contenga:

```python
path("", map_page, name="home_page")
```

### Gli alert email non partono

Controllare le variabili SMTP e usare credenziali valide nel provider di test configurato.

## File richiesti per la consegna

La consegna finale include almeno questi elementi:[cite:513]
- codice sorgente completo di Problema 1 e Problema 2;
- `README.md` con struttura, installazione, esecuzione e test;
- `Dockerfile` per il backend;
- configurazione PostgreSQL separata;
- test automatici;
- file di descrizione teorica del Problema 2.
