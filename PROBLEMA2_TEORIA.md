# Problema 2 — Descrizione teorica

## 1. Spiegazione teorica della soluzione per acquisire e ricostruire, nel tempo, le sequenze di valori X

### 1.1 Il problema di fondo

L'API del Problema 1 (`POST /api/simulation/`) è **stateless per costruzione**: riceve in ingresso lo stato dell'ultima iterazione nota (`events`) e restituisce il nuovo stato, senza mantenere memoria implicita tra una chiamata e l'altra. Chiamata dopo chiamata, ogni evento (`index`) evolve nel proprio valore `X`, ma **nulla di questa storia sopravvive** se non viene esplicitamente salvato lato server — mentre l'obiettivo del Problema 2 è proprio ricostruire, per ciascun evento, l'intera sequenza dei valori `X` assunti nel tempo.

La soluzione deve quindi introdurre uno strato di **persistenza esterna** alla API stateless, capace di:
1. tracciare univocamente ogni evento generato durante una sequenza di chiamate;
2. registrare il valore di `X` di ciascun evento per ciascun giorno (DOY) osservato;
3. permettere, in un secondo momento, di interrogare questa storia per un singolo evento o per l'insieme degli eventi attivi in un dato giorno.

### 1.2 Modello dati adottato

La persistenza è organizzata su due entità, mappate su altrettante tabelle PostgreSQL (`simulation/models.py`):

- **`ModelRun`**: rappresenta una singola sequenza di elaborazione (una "batch run"), identificata da `first_doy` e `last_doy`. Ogni chiamata a `/api/oidio-batch/` o a `/api/oidio-batch/openmeteo/today/` crea una nuova riga.
- **`EventSnapshot`**: rappresenta il valore di `X` di un dato evento (`event_index`) in un dato giorno (`doy`), all'interno di una specifica run, con foreign key verso `ModelRun`. È presente un vincolo di unicità composito su `(run, doy, event_index)`.

L'evento non è dunque un'entità globale indipendente: è identificato dal proprio `event_index` **all'interno di una run**. La run è il contenitore temporale, gli `EventSnapshot` ne sono le osservazioni puntuali giorno per giorno. Questa scelta rispecchia fedelmente la semantica del Problema 1, dove gli `index` sono generati in modo incrementale e locale a una singola sequenza di chiamate stateless (ripartono da zero ogni volta che non viene fornito uno stato `events` pregresso), e non sono pensati come identificativi persistenti tra sequenze diverse.

### 1.3 Flusso di acquisizione

Ad ogni chiamata batch (una sequenza `days` di dati meteo storici e previsionali, con lo stato iniziale `events` relativo al giorno immediatamente precedente al primo DOY della sequenza, come richiesto esplicitamente dalla consegna):

1. Si crea una nuova riga `ModelRun`, con `first_doy`/`last_doy` desunti dalla sequenza ricevuta.
2. Per ciascun giorno della sequenza, in ordine cronologico, si invoca il Problema 1 come black-box, passando come stato iniziale l'output della chiamata al giorno precedente (`current_events`) — esattamente la logica "a macchina a stati" richiesta dal Problema 1, semplicemente iterata più volte all'interno di un'unica richiesta HTTP.
3. Per ciascun evento presente nell'output di quel giorno, si crea o si aggiorna una riga `EventSnapshot` tramite un'operazione di *upsert* (`update_or_create`) sulla chiave `(run, doy, event_index)`.

L'upsert garantisce **idempotenza**: se lo stesso giorno della stessa run venisse rielaborato (ad esempio a seguito di un errore e di un nuovo tentativo), il valore viene sovrascritto anziché duplicato, evitando serie temporali con osservazioni multiple e contraddittorie per lo stesso `(evento, giorno)`.

### 1.4 Ricostruzione della serie temporale

Per ricostruire l'andamento nel tempo di un evento, l'endpoint `GET /api/runs/<id>/` interroga tutti gli `EventSnapshot` associati a quella run, li ordina per `doy` e li raggruppa per `event_index`. Il vincolo di unicità composito, supportato da un indice B-tree lato PostgreSQL, rende efficiente sia l'interrogazione "storia completa di un evento" sia quella "tutti gli eventi attivi in un dato giorno" — i due pattern di accesso realmente richiesti dal problema (si veda il punto 3 per il dettaglio delle complessità).

---

## 2. Implementazione della soluzione: Problema 1 come black-box ed eventuali aggiustamenti

### 2.1 Problema 1 utilizzato senza modifiche interne

La consegna specifica che il Problema 1 va trattato, nel contesto del Problema 2, come una **black-box**: se ne conosce la struttura JSON di input/output, ma non (concettualmente) la logica interna di generazione dei valori di `X`. Nell'implementazione realizzata, questo principio è rispettato in modo diretto: la funzione `run_problem1_blackbox` (in `simulation/services.py`) — che incapsula `update_events` e `should_create_event`, ovvero l'intera logica del Problema 1 — **non è stata modificata** per supportare il Problema 2. Riceve un singolo giorno (`doy`, `temperature`, `bagnatura`, `humidity`, `rain`, `events`) e restituisce il nuovo stato, esattamente come specificato per il Problema 1 stand-alone, indipendentemente dal fatto che venga chiamata da `simulation_api` (endpoint diretto del Problema 1) o dall'orchestrazione del Problema 2.

### 2.2 L'aggiustamento richiesto: dove è stato collocato

La consegna anticipa che la API del Problema 1 "andrà opportunamente modificata" per accettare, nel Problema 2, **input multi-giornalieri** invece di un singolo giorno per chiamata. Nella soluzione realizzata, questo adattamento **non è stato implementato modificando `run_problem1_blackbox`**, bensì introducendo uno **strato di orchestrazione esterno e superiore** ad essa: la funzione `run_batch_and_persist` (in `simulation/views.py`), che:

- riceve una sequenza `days` (potenzialmente multi-giorno, storica e previsionale);
- itera su di essa giorno per giorno, invocando ad ogni iterazione `run_problem1_blackbox` con un singolo giorno alla volta e propagando lo stato (`current_events`) da un'iterazione alla successiva;
- accumula gli output e li persiste come `EventSnapshot`.

Questa collocazione dell'aggiustamento è una scelta progettuale deliberata, motivata da due ragioni:

1. **Preservare la vera natura black-box del Problema 1.** Se la logica multi-giorno fosse stata incorporata dentro `run_problem1_blackbox`, quest'ultima non sarebbe più stata la stessa funzione riutilizzabile e testabile in isolamento richiesta come endpoint a sé stante (`/api/simulation/`); si sarebbe introdotta una dipendenza concettuale del Problema 1 dal Problema 2, invertendo la relazione di riuso richiesta dalla consegna.
2. **Separazione delle responsabilità.** Il Problema 1 resta responsabile unicamente della transizione di stato per un singolo giorno (la "macchina a stati" elementare); il Problema 2 è responsabile dell'orchestrazione temporale (iterazione sui giorni), della finestra di dati multi-giorno (un giorno storico più sette di previsione, costruita da `build_problem2_today_window`) e della persistenza. Ciascuno dei due livelli è verificabile e testabile separatamente, coerentemente con la suddivisione dei test richiesti dalla consegna (`test_problem1_api.py` isolato da `test_problem2_api.py`).

In sintesi: l'"aggiustamento a rendere la simulazione coerente con quanto richiesto dal Problema 2" esiste, ma è stato realizzato come **wrapper di orchestrazione attorno al Problema 1**, e non come modifica del suo codice interno — un'interpretazione che soddisfa il requisito funzionale (accettare sequenze multi-giorno) mantenendo intatta l'indicazione di trattare il Problema 1 come componente a sé stante e non toccarne la logica di generazione.

---

## 3. Stime di complessità algoritmica (tempo e spazio, notazione O-grande)

Si definiscono i seguenti parametri, usati nelle stime che seguono:

- `n` = numero di giorni elaborati in una singola chiamata batch (lunghezza di `days`);
- `e_t` = numero di eventi complessivamente creati fino al giorno `t` all'interno della run corrente (monotono non decrescente in `t`);
- `E` = numero totale di eventi distinti creati al termine della run (`E = e_n`, limite superiore di `e_t` per ogni `t`);
- `m` = numero totale di righe `EventSnapshot` presenti in una run (al più `n · E`, tipicamente molto meno, poiché non tutti gli eventi sono attivi in tutti i giorni della loro esistenza logica);
- `r` = numero di run salvate nel database;
- `s` = numero totale di `EventSnapshot` nell'intero database (su tutte le run).

### 3.1 Aggiornamento/creazione di uno snapshot — `EventSnapshot.objects.update_or_create(...)`

- **Tempo**: **O(log s)**. L'operazione di upsert sfrutta l'indice univoco composito su `(run, doy, event_index)`; PostgreSQL implementa tale indice come B-tree, per cui la ricerca della riga esistente (ed il conseguente update o insert) costa O(log s) rispetto al numero totale di righe indicizzate, non O(1) in senso stretto — approssimabile a costo pressoché costante solo per la scala di dati di un singolo test, ma la stima rigorosa in notazione O-grande resta logaritmica.
- **Spazio**: **O(1)** aggiuntivo per singola operazione (una riga di dimensione costante); l'indice stesso occupa O(s) complessivamente, ma tale costo è ammortizzato sull'intera base dati, non sulla singola operazione.

### 3.2 Elaborazione di un'intera run batch — `run_batch_and_persist`

- **Tempo**: **O(n · E)**. Per ciascuno degli `n` giorni si esegue `update_events`, che itera sugli eventi esistenti fino a quel momento (al più `E`, poiché anche gli eventi già maturi con `X = 1` vengono comunque riscritti come costanti), più un'eventuale creazione di nuovo evento in tempo O(1); a ciò si aggiunge, per ciascun evento aggiornato in ciascun giorno, un'operazione di upsert O(log m) (si veda 3.1, qui `m` al posto di `s` poiché l'indice è comunque globale ma la porzione rilevante per la run è O(m)). Il termine dominante resta quindi **O(n · E · log m)** se si vuole includere anche il costo di persistenza, o **O(n · E)** se si considera la sola componente di calcolo in memoria.
- **Spazio**: **O(n · E)**, per la lista `all_outputs` che accumula in memoria l'output di ciascun giorno prima di restituire la risposta, oltre alle `m ≤ n · E` righe effettivamente persistite su disco.

Si osservi che, nella pratica, `E` cresce solo quando le condizioni di creazione di un nuovo evento (`should_create_event`) sono soddisfatte, per cui il caso tipico è significativamente più favorevole del caso peggiore `E = n` (un nuovo evento ad ogni giorno).

### 3.3 Ricostruzione della serie storica di un singolo evento o di tutti gli eventi di una run — `run_detail_api`

- **Tempo**: **O(m log m)**. Gli `EventSnapshot` della run vengono recuperati con una singola query ordinata (`order_by("doy", "event_index")`), il cui costo, sfruttando l'indice esistente, è O(m log m) nel caso peggiore lato database (o O(m) se l'ordinamento può sfruttare direttamente l'indice B-tree già ordinato su quelle colonne); il successivo raggruppamento per `event_index` e la costruzione delle serie punto-per-punto in Python avvengono in **O(m)**, con strutture ausiliarie a dizionario per l'accesso O(1) ammortizzato al valore di un evento in un dato giorno.
- **Spazio**: **O(m)**, per la lista `snapshot_rows`, le strutture `event_series` (una lista di punti per ciascuno degli eventi distinti nella run) e `summary_by_day` (un'aggregazione per ciascuno dei giorni distinti, al più `n`).

Questo è il pattern di accesso centrale richiesto dal Problema 2 ("ricostruire, per ciascun evento, l'andamento temporale del proprio valore descrittivo X"): la scelta di normalizzare i dati in `EventSnapshot` anziché salvare l'intero array `events` come blob JSON per ogni chiamata è ciò che rende possibile eseguire questa ricostruzione in tempo lineare nel numero di osservazioni pertinenti, invece che dover deserializzare e scansionare linearmente ogni singolo blob storico.

### 3.4 Elenco delle run con conteggio degli snapshot — `runs_api`

- **Tempo**: **O(r + s)** complessivo, di cui la parte di aggregazione (`annotate(Count("snapshots"))`) è eseguita interamente lato database come `GROUP BY` sull'indice della foreign key `run_id`, con costo O(s) per la scansione/aggregazione a livello di motore SQL; il livello applicativo riceve poi solo **O(r)** righe già aggregate.
- **Spazio**: **O(r)** lato applicativo (una riga di riepilogo per run); il calcolo intermedio di aggregazione è gestito internamente dal database e non richiede all'applicazione di caricare in memoria i singoli `EventSnapshot`.

### 3.5 Motivazione complessiva della scelta delle strutture dati

La normalizzazione in due tabelle relazionali (`ModelRun`, `EventSnapshot`) con indice composito è stata preferita a due alternative più semplici da implementare, per le seguenti ragioni legate direttamente alle complessità sopra stimate:

- **Alternativa scartata — un'unica riga con colonna JSON contenente l'intero array `events` per ogni chiamata**: la ricostruzione della storia di un singolo evento richiederebbe di deserializzare e scansionare **ogni** blob JSON della run (costo O(n) blob, ciascuno di dimensione O(E), quindi O(n · E) solo per l'accesso, senza alcun beneficio dall'indicizzazione), contro l'O(m) ottenuto con la normalizzazione.
- **Alternativa scartata — salvare solo l'ultimo stato per run** (comportamento nativo, non persistito, del solo Problema 1): costo O(1) in scrittura, ma **impossibilità strutturale** di rispondere alla query richiesta dal Problema 2 ("ricostruire nel tempo"), poiché l'informazione storica non esisterebbe più dopo l'ultima chiamata.
- **Soluzione adottata**: paga un costo di scrittura leggermente superiore (O(log s) per upsert indicizzato anziché O(1) per un semplice append di stato) in cambio di un costo di lettura/ricostruzione lineare O(m) invece che lineare nel numero di blob non indicizzabili — un compromesso favorevole poiché, nel dominio del problema, le operazioni di ricostruzione (lette dalla Dashboard, potenzialmente ripetute) sono attese più frequenti delle singole scritture di uno snapshot.
