# Primo Principio — Test Tecnico Full-Stack

[![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-A30000?logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-316192?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Highcharts](https://img.shields.io/badge/Highcharts-12.4.0-0071C5)](https://www.highcharts.com/)

Il presente repository contiene la soluzione ai task tecnici front-end e back-end proposti da Primo Principio: calcolo dei **Gradi Giorno**, visualizzazione geografica del rischio (pagina "mappa"), modello previsionale (pagina "modello"), una pagina "Dashboard" di monitoraggio delle chiamate API, e due API di simulazione di eventi biologici (Problema 1 — modello generico a eventi, Problema 2 — modello Oidio con persistenza storica).

## Indice

- [Struttura del progetto](#struttura-del-progetto)
- [Scelte progettuali e librerie](#scelte-progettuali-e-librerie)
- [Installazione delle dipendenze](#installazione-delle-dipendenze)
- [Avvio rapido (Docker)](#avvio-rapido-docker)
- [Variabili d'ambiente](#variabili-dambiente)
- [Pagina Mappa e pagina Modello](#pagina-mappa-e-pagina-modello)
- [Pagina Dashboard](#pagina-dashboard)
- [Endpoint API](#endpoint-api)
- [Problema 1 (API a eventi)](#problema-1-api-a-eventi)
- [Problema 2 (modello Oidio + persistenza)](#problema-2-modello-oidio--persistenza)
- [Esempi di input/output](#esempi-di-inputoutput)
- [Logica di calcolo dei Gradi Giorno](#logica-di-calcolo-dei-gradi-giorno)
- [Test automatici](#test-automatici)
- [Complessità algoritmica (Problema 2)](#complessità-algoritmica-problema-2)

## Struttura del progetto

Si osservi di seguito l'organizzazione delle directory e dei file principali del progetto:

```text
primoprincipio_project/
├── config/                     # Configurazione Django (settings, routing, wsgi/asgi)
├── simulation/
│   ├── models.py                # ModelRun, EventSnapshot, AlertThreshold
│   ├── services.py              # Regole di crescita X, orchestrazione Problema 1/2, client Open-Meteo (dati giornalieri)
│   ├── views.py                 # Endpoint API + viste pagina mappa/modello/dashboard
│   ├── urls.py
│   ├── migrations/
│   └── test/
│       ├── test_problem1_api.py
│       ├── test_problem2_api.py
│       └── test_reconstruction.py
├── static/
│   ├── css/          
│   └── js/                      # Codice Google Maps e Highcharts, separato dai template
├── templates/
│   ├── head.html                 # Header condiviso, menù di navigazione, link al CSS
│   ├── map.html                  # Pagina "mappa"
│   ├── model.html                 # Pagina "modello"
│   └── dashboard.html             # Pagina "Dashboard"
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── requirements.txt
└── README.md
```

## Scelte progettuali e librerie

- **Django + Django REST Framework**: unico stack adottato sia per il front-end (template server-side) sia per il back-end (API REST), in linea con l'opzione "mista" indicata nella consegna.
- **[Highcharts](https://www.highcharts.com/) 12.4.0** (via CDN jsdelivr): libreria richiesta esplicitamente per il grafico Line Chart della pagina "modello", riutilizzata anche nella Dashboard per la visualizzazione dei risultati delle API.
- **[Google Maps JavaScript API](https://developers.google.com/maps/documentation/javascript)**: utilizzata nella pagina "mappa", con stile satellite forzato tramite `mapTypeId: 'satellite'` e marker personalizzato colorato dinamicamente (verde/giallo/rosso).
- **[Open-Meteo API](https://open-meteo.com/)** (endpoint `archive` e `forecast`, aggregazione giornaliera): fonte dei dati meteo per il calcolo dei Gradi Giorno e per l'alimentazione delle API del Problema 1 e del Problema 2.
- **PostgreSQL come servizio Docker separato** (`postgres:15`): richiesto esplicitamente per la persistenza del Problema 2; non è incluso nell'immagine del backend.
- **Nessun template Bootstrap di partenza**: il CSS è stato scritto da zero in `static/css/style.css`, incluso tramite `head.html`, condiviso da tutte le pagine.
- **JS separato dal template**: il codice di integrazione di Google Maps e di Highcharts risiede in file `.js` dedicati sotto `static/js/`, distinti dai file di template, come richiesto esplicitamente dalla consegna.

## Installazione delle dipendenze

Le dipendenze Python del progetto sono elencate in `requirements.txt`. Si può procedere in due modi equivalenti:

- **Via Docker (consigliato)**: non è richiesta alcuna installazione manuale — si esegua `docker compose up --build` e le dipendenze verranno installate automaticamente all'interno del container, garantendo un ambiente riproducibile indipendente dalla macchina.
- **Manualmente, senza Docker**: si crei un ambiente virtuale e si installino le dipendenze come segue.
  ```bash
  python -m venv .venv
  .venv\Scripts\activate      # Windows
  source .venv/bin/activate   # macOS/Linux

  pip install -r requirements.txt
  ```
  In questo caso è necessaria un'istanza PostgreSQL raggiungibile localmente, con credenziali configurabili tramite le variabili d'ambiente (si veda la sezione dedicata).

## Avvio rapido (Docker)

### Avvio completo

Clonare la repository git con:
```bash
git clone https://github.com/Gerocoo/primoprincipio
```


Si acceda alla cartella effettiva dell'applicativo con:
```bash
cd <path_to>\primoprincipio\primoprincipio_project
```


Si avviino i container con:

```bash
docker compose up --build
```

Questo comando costruisce l'immagine del backend e avvia anche il database PostgreSQL come servizio separato. Se il sistema è partito correttamente, si dovrebbero osservare:
- il container del database `db` attivo;
- il container del backend `web` attivo;
- il server Django raggiungibile su `http://localhost:8000`.

### Avvio in background

Per lavorare in background, si usi:

```bash
docker compose up -d --build
```

In questo modo i container restano avviati senza bloccare il terminale.

### Dopo l'avvio

Si eseguano le migrazioni, se non sono già state applicate:

```bash
docker compose exec web python manage.py migrate
```

Si crei un superuser, qualora sia necessaria la dashboard di amministrazione di Django:

```bash
docker compose exec web python manage.py createsuperuser
```

Si apra quindi il browser sui seguenti indirizzi:
- Pagina mappa: **http://localhost:8000/map/**
- Pagina modello: **http://localhost:8000/model/**
- Pagina Dashboard: **http://localhost:8000/dashboard/**

### Stop dei container

Quando si è terminato, si esegua:

```bash
docker compose down
```

Se si desidera eliminare anche i dati del database (reset completo), si esegua invece:

```bash
docker compose down -v
```

### Costruzione ed esecuzione separata dei container

Come richiesto esplicitamente dalla consegna, di seguito si riportano le istruzioni per costruire ed eseguire backend e database come container distinti, senza ricorrere a `docker compose`.

Si costruisca anzitutto l'immagine del backend:

```bash
docker build -t primoprincipio-backend .
docker network create primoprincipio_net
```

Si avvii quindi il database PostgreSQL come servizio a sé stante:

```bash
docker run --name primoprincipio_db `
  --network primoprincipio_net `
  -e POSTGRES_DB=primoprincipio `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -p 5432:5432 `
  -v postgres_data:/var/lib/postgresql/data `
  -d postgres:15
```

Infine si esegua il backend collegato al database:

```bash
docker run --name primoprincipio_web `
  --network primoprincipio_net `
  -e DB_ENGINE=django.db.backends.postgresql `
  -e POSTGRES_DB=primoprincipio `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_HOST=primoprincipio_db `
  -e POSTGRES_PORT=5432 `
  -e GOOGLE_MAPS_API_KEY=<la-propria-chiave> `
  -p 8000:8000 `
  primoprincipio-backend
```

## Variabili d'ambiente

Si riportano di seguito i valori usati come default in `docker-compose.yml` (da spostare in un file `.env` non versionato per un utilizzo reale):

```env
DJANGO_SECRET_KEY=dev-secret-key
DEBUG=1
ALLOWED_HOSTS=*
DB_ENGINE=postgres
POSTGRES_DB=primoprincipio
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432
EMAIL_HOST=sandbox.smtp.mailtrap.io
EMAIL_PORT=2525
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=1
DEFAULT_FROM_EMAIL=assistenza@primoprincipio.it
GOOGLE_MAPS_API_KEY=
```

> **Nota sulle email:** per il corretto funzionamento dell’invio mail è consigliabile utilizzare il servizio online [Mailtrap](https://mailtrap.io/), creando un account dedicato. Una volta ottenute le credenziali SMTP, si compilino le variabili corrispondenti nel file `.env` (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`), lasciando il resto invariato. 

> **Nota visualizzazione mappa:** per la corretta visualizzazione della pagina "Mappa" è indispensabile utilizzare una chiave valida per le [Google Maps JavaScript API](https://developers.google.com/maps/documentation/javascript/get-api-key). Si crei un progetto Google Cloud, si abiliti l’API e si imposti la variabile `GOOGLE_MAPS_API_KEY` nel file `.env`, lasciando invariato il resto della configurazione.


## Pagina Mappa e pagina Modello

**Pagina Mappa** (`/map/`, `templates/map.html`): si veda un marker Google Maps centrato sul pin `45.657808639037725, 13.846673204128058`, con `mapTypeId: 'satellite'`, zoom fisso a 13 e mappa navigabile. Il colore del marker (verde/giallo/rosso) è determinato dinamicamente in base al rischio calcolato server-side. Al passaggio del mouse sul pin compare una InfoWindow con Rischio, Gradi Giorno attuali, soglia e azione consigliata; è presente inoltre una legenda dei colori come controllo custom sulla mappa. Cliccando sul marker si viene reindirizzati alla pagina "modello".

**Pagina Modello** (`/model/`, `templates/model.html`): si veda un grafico Highcharts di tipo Line Chart con la serie dei Gradi Giorno cumulati per DOY, una linea verticale rossa sul giorno corrente, una linea orizzontale arancione per la soglia Sordidus e linee rosse tratteggiate per ogni soglia di allarme attiva. È inoltre presente un form per la gestione delle soglie: creazione (valore + email), attivazione/disattivazione, cancellazione consentita solo se la soglia è disattivata (vincolo verificato lato API, con messaggio d'errore in caso contrario).

## Pagina Dashboard

**Pagina Dashboard** (`/dashboard/`, `templates/dashboard.html`), raggiungibile dal menù di navigazione condiviso (`head.html`) insieme alle pagine "Mappa" e "Modello": è la pagina pensata per monitorare, in forma grafica, l'esito delle chiamate alle API di simulazione del Problema 2, ossia:

```python
path("api/oidio-batch/", oidio_batch_api, name="oidio_batch_api"),
path("api/oidio-batch/openmeteo/today/", oidio_batch_openmeteo_today_api, name="oidio_batch_openmeteo_today_api"),
```

A differenza della pagina "modello", che mostra un singolo scenario di Gradi Giorno, la Dashboard offre una **vista aggregata e storica delle simulazioni Oidio**: ogni chiamata a `oidio-batch` (manuale o automatica via Open-Meteo) produce una nuova `ModelRun`, e la Dashboard ne recupera l'elenco tramite `/api/runs/` per rappresentarla graficamente. In particolare, si propone che la pagina mostri:

- un **grafico Highcharts a linee multiple**, una per ciascun `event_index` della run selezionata, con l'andamento del valore `X` nel tempo (asse orizzontale: DOY; asse verticale: `X` da 0 a 1) — così da rendere immediatamente visibile la crescita monotona di ogni evento fino alla maturazione (`X = 1`);
- un **selettore delle run** (elenco `ModelRun` con relativo intervallo `first_doy`–`last_doy` e numero di eventi), per confrontare l'esito di chiamate diverse alla stessa API;
- un **riepilogo numerico** per la run selezionata (numero di eventi attivi, numero di eventi maturati, valore medio di `X`), utile per una lettura rapida senza dover interpretare il grafico nel dettaglio.

Questa pagina consente quindi, in fase di verifica del lavoro svolto, di richiamare le API del Problema 2 (anche più volte, con dati diversi) e di osservarne l'esito senza dover leggere manualmente il JSON restituito o interrogare direttamente il database.

## Endpoint API

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/api/simulation/` | Problema 1 — singola chiamata giornaliera, stateless (riceve/restituisce `events`) |
| `POST` | `/api/oidio-batch/` | Problema 2 — chiamata multi-DOY con persistenza su DB (`days` + `events` iniziali in input) |
| `POST` | `/api/oidio-batch/openmeteo/today/` | Problema 2 — variante che recupera automaticamente da Open-Meteo il giorno storico "ieri" + 7gg di previsione |
| `GET` | `/api/runs/` | Elenco delle run salvate (con conteggio snapshot), usato dalla Dashboard |
| `GET` | `/api/runs/<id>/` | Dettaglio di una run: snapshot grezzi, serie per evento, riepilogo giornaliero |
| `GET/POST/PATCH/DELETE` | `/api/alerts/` | CRUD delle soglie di allarme (creazione, attivazione/disattivazione, cancellazione con vincolo "solo se disattivata") |
| `GET` | `/api/alerts/list/` | Elenco soglie salvate, usato dal front-end per popolare il grafico della pagina "modello" |
| `GET` | `/map/`, `/model/`, `/dashboard/` | Pagine HTML |

## Problema 1 (API a eventi)

Endpoint: `POST /api/simulation/`

Si osservi la logica implementata:
- Si ricevono in input `doy`, `temperature`, `bagnatura`, `humidity`, `rain`, e opzionalmente `events` (a partire dalla seconda chiamata).
- Un nuovo evento viene creato quando `bagnatura=1 AND rain>0`, oppure quando `bagnatura=1 AND humidity>80 AND temperature>15` (`should_create_event`).
- Per ogni evento esistente con `X < 1`, si applica una tra tre regole di crescita, scelta casualmente ad ogni chiamata (`growth_rules`):
  1. `X = X + 0.1`
  2. `X = X + 0.2`
  3. `X = X + (1 - X) * 0.35` (avvicinamento asintotico a 1)
  - Tutte le regole sono limitate superiormente a `min(1.0, ...)`, così da garantire `0 ≤ X ≤ 1` e monotonia non decrescente.
- Un evento con `X ≥ 1.0` resta costante, senza ulteriore crescita.
- L'API è stateless: non è prevista alcuna persistenza in questo endpoint — lo stato transita interamente nel payload di richiesta e risposta.

## Problema 2 (modello Oidio + persistenza)

Endpoint: `POST /api/oidio-batch/` (chiamata manuale) e `POST /api/oidio-batch/openmeteo/today/` (chiamata automatica da Open-Meteo)

Si osservi che:
- la logica del Problema 1 viene riutilizzata come **black-box** (`run_problem1_blackbox`), applicata iterativamente giorno per giorno su una sequenza `days` di dati storici e previsionali;
- la variante `.../openmeteo/today/` costruisce automaticamente la finestra richiesta dalla consegna: un giorno storico ("ieri") dall'endpoint `archive` più sette giorni di previsione dall'endpoint `forecast` di Open-Meteo (`build_problem2_today_window`);
- ogni sequenza di chiamate batch viene tracciata come riga `ModelRun` (con `first_doy`/`last_doy`); ogni valore `X` di ogni evento in ogni DOY viene salvato come riga `EventSnapshot`, collegata alla run tramite foreign key, con vincolo di unicità `(run, doy, event_index)` per evitare duplicati in caso di rielaborazione dello stesso giorno.

Per la spiegazione teorica rigorosa della logica di persistenza e ricostruzione, si veda [`PROBLEMA2_TEORIA.md`](./PROBLEMA2_TEORIA.md).

## Esempi di input/output

Di seguito alcuni esempi a supporto della comprensione del funzionamento, come richiesto dalla consegna.

### Problema 1 — prima chiamata (creazione di un nuovo evento)

Si esegua:

```bash
curl -X POST http://localhost:8000/api/simulation/ \
  -H "Content-Type: application/json" \
  -d '{
    "doy": 126,
    "temperature": 15.94,
    "bagnatura": 1,
    "humidity": 97.25,
    "rain": 0.0
  }'
```

Si ottiene in risposta:
```json
{
  "doy": 126,
  "events": [
    { "index": 0, "X": 0.0 }
  ]
}
```

### Problema 1 — seconda chiamata (evoluzione dell'evento esistente)

Si esegua:

```bash
curl -X POST http://localhost:8000/api/simulation/ \
  -H "Content-Type: application/json" \
  -d '{
    "doy": 127,
    "temperature": 17.15,
    "bagnatura": 1,
    "humidity": 42.35,
    "rain": 0.0,
    "events": [ { "index": 0, "X": 0.0 } ]
  }'
```

Si ottiene in risposta (il valore di X cresce secondo una delle tre regole, scelta casualmente):
```json
{
  "doy": 127,
  "events": [
    { "index": 0, "X": 0.2 }
  ]
}
```

### Problema 2 — chiamata batch multi-DOY (Oidio, con persistenza)

Si esegua:

```bash
curl -X POST http://localhost:8000/api/oidio-batch/ \
  -H "Content-Type: application/json" \
  -d '{
    "days": [
      { "doy": 275, "temperature": 30.0, "bagnatura": 0, "humidity": 32.0, "rain": 0.0 },
      { "doy": 276, "temperature": 28.0, "bagnatura": 0, "humidity": 30.0, "rain": 0.0 },
      { "doy": 277, "temperature": 27.0, "bagnatura": 1, "humidity": 59.0, "rain": 22.0 }
    ],
    "events": [
      { "index": 0, "X": 0.7 }
    ]
  }'
```

Si ottiene in risposta un riepilogo della run (ogni DOY genera inoltre uno snapshot persistito su `EventSnapshot`):
```json
{
  "run_id": 12,
  "days": [
    { "doy": 275, "events": [ { "index": 0, "X": 0.7 } ] },
    { "doy": 276, "events": [ { "index": 0, "X": 0.9 } ] },
    { "doy": 277, "events": [ { "index": 0, "X": 1.0 }, { "index": 1, "X": 0.0 } ] }
  ]
}
```

### Problema 2 — variante automatica con dati reali Open-Meteo

Si esegua:

```bash
curl -X POST http://localhost:8000/api/oidio-batch/openmeteo/today/ \
  -H "Content-Type: application/json" \
  -d '{ "lat": 45.657808639037725, "lng": 13.846673204128058, "events": [] }'
```

Si osservi che questa chiamata recupera automaticamente il dato storico di "ieri" e sette giorni di previsione da Open-Meteo, esegue la sequenza sul Problema 1 come black-box e persiste il risultato in una nuova `ModelRun`, visibile poi nella pagina Dashboard.

### Ricostruzione della serie storica di un evento

Si esegua:

```bash
curl http://localhost:8000/api/runs/12/
```

Si ottiene:
```json
{
  "run_id": 12,
  "first_doy": 275,
  "last_doy": 277,
  "events": {
    "0": [ { "doy": 275, "X": 0.7 }, { "doy": 276, "X": 0.9 }, { "doy": 277, "X": 1.0 } ],
    "1": [ { "doy": 277, "X": 0.0 } ]
  }
}
```


## Logica di calcolo dei Gradi Giorno

```
DD_giorno = max(0, Tmean - Tth)
DD_cumulato(t) = Σ DD_giorno  dal 1° gennaio a t
```

Si noti che `Tth = 8°C`, e che i dati meteo giornalieri (`temperature_2m_mean`) sono recuperati da Open-Meteo tramite `simulation/services.py`, unica fonte del calcolo usata da entrambe le pagine `/map/` e `/model/`. La soglia di rischio Sordidus è allineata al valore di specifica: **106.8 DD**.

## Test automatici

Per eseguire tutti i test, si lanci:
```bash
docker compose exec web python manage.py test
```

Per limitarsi all'app di simulazione (Problema 1 e Problema 2), si esegua invece:
```bash
docker compose exec web python manage.py test simulation.test
```

Si noti che sono coperti dai test:
- la corretta creazione di un evento al verificarsi delle condizioni previste (`test_problem1_api.py`);
- il rispetto del vincolo `0 ≤ X ≤ 1` e la monotonia non decrescente;
- la corretta gestione di più chiamate multi-DOY e della relativa persistenza (`test_problem2_api.py`);
- la corretta ricostruzione della serie storica per singolo evento a partire dagli `EventSnapshot` (`test_reconstruction.py`).

## Complessità algoritmica (Problema 2)

Si riportano di seguito le stime di complessità delle principali operazioni coinvolte nella gestione e ricostruzione delle serie temporali, con la relativa motivazione della struttura dati adottata.

| Operazione | Complessità | Note |
|---|---|---|
| Aggiornamento/creazione snapshot per un evento in un DOY | O(1) | `update_or_create` su chiave composita indicizzata `(run, doy, event_index)` |
| Elaborazione di una run di `n` giorni con `k` eventi mediamente attivi | O(n·k) | Un ciclo di aggiornamento eventi più un'eventuale creazione, per ciascun giorno della sequenza |
| Ricostruzione della serie storica di un singolo evento (`run_detail_api`) | O(m) | `m` = numero di snapshot della run; filtro e raggruppamento in memoria per `event_index` |
| Elenco delle run con conteggio snapshot (`runs_api`), usato dalla Dashboard | O(r + s) | `r` = numero di run, `s` = numero totale di snapshot, tramite `annotate(Count(...))` a livello DB |
