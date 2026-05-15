# FastCall

> Platformă SaaS de tip *call-center virtual*: fiecare companie își înrolează propriul „operator” conversațional bazat pe LLM, alimentat din **propria** bază de cunoștințe (PDF-uri, documente interne) și din **propria** bază de date de clienți. Utilizatorii finali pot dialoga cu acest operator fie prin chat text, fie prin apel vocal hands-free direct în browser.

---

## 1. Ideea proiectului

În call-center-ele clasice, fiecare cerere a unui client (informații despre un produs, status comandă, politici de retur etc.) ajunge la un operator uman care consultă manual documentația și CRM-ul. FastCall propune înlocuirea acestui flux de „primă linie” cu un **agent conversațional per-tenant**, care:

- *Citește* baza de cunoștințe a companiei (PDF-uri cu politici, manuale, FAQ-uri) printr-un mecanism de **Retrieval-Augmented Generation (RAG)**.
- *Interoghează* în mod read-only baza de date proprie a companiei pentru întrebări specifice contului unui client.
- *Învață în timp* din conversațiile încheiate cu succes, extrăgând automat perechi întrebare/răspuns generice într-un **FAQ cache** care răspunde instant la întrebări repetate, fără a mai apela LLM-ul.
- Oferă utilizatorului final atât interfață **chat** (text), cât și **voice call** complet hands-free (Web Speech API), cu transcript live.
- Generează la final un **ticket** persistent (cu status `successful` / `failed`) — sursa de adevăr pentru audit și pentru extracția FAQ.

Sistemul este **multi-tenant** prin izolare la nivel de date: fiecare call center are propriul director `data/cc_<id>/` cu colecție Chroma și FAQ JSON proprii, propriul URI de bază de date pentru clienți, și propria parolă/cont. Două call center-uri nu pot „să se vadă” niciodată reciproc, prin construcție.

### Roluri / actori

| Rol | Ce poate face |
|---|---|
| **Call center** (admin) | Se înregistrează cu nume, domeniu, descriere, URI bază de date proprie. Urcă PDF-uri în knowledge base. Are propriul dashboard. |
| **Client** (utilizator final) | Se înregistrează atașat la un call center existent. Deschide conversații (chat sau voce), primește răspunsuri, închide conversația marcând-o ca rezolvată sau nu. Vede istoricul propriilor tichete. |

---

## 2. Stack tehnologic

### Backend (`@D:/Licenta/app`)

| Tehnologie | Versiune | Rol |
|---|---|---|
| **Python** | 3.11+ | Limbaj backend |
| **FastAPI** | 0.128 | Framework HTTP, OpenAPI auto-generat |
| **Uvicorn** | 0.40 | ASGI server |
| **SQLAlchemy** | 2.1 | ORM peste baza de date principală a platformei |
| **PostgreSQL** (via `psycopg2-binary`) | — | Stocare pentru `call_centers`, `clients`, `tickets`, `messages`, `revoked_tokens` |
| **Pydantic v2** + `pydantic-settings` | 2.12 | Validare DTO + încărcare config din `.env` |
| **python-jose** + `bcrypt` / `passlib` | — | Emitere / verificare JWT, hash de parole |
| **OpenAI SDK** | 1.55 | Chat completions (`gpt-4o-mini`) și embeddings (`text-embedding-3-small`) |
| **ChromaDB** | 0.5.20 | Vector store persistent per tenant pentru RAG |
| **pypdf** | 6.7 | Extracție text din PDF la indexare |
| **pytest** | 9.0 | Testare unitară a layer-ului de persistență |

### Frontend (`@D:/Licenta/client`)

| Tehnologie | Versiune | Rol |
|---|---|---|
| **React** | 19.2 | SPA |
| **React Router** | 6.8 | Rutare client-side |
| **Axios** | 1.6 | Client HTTP cu interceptor de JWT |
| **TailwindCSS** | 3.3 | Styling utility-first |
| **Headless UI** + **Heroicons** + **Lucide** | — | Componente accesibile și iconografie |
| **Web Speech API** (nativă în browser) | — | STT (`webkitSpeechRecognition`) și TTS (`speechSynthesis`) pentru apelul vocal — fără server media |

---

## 3. Arhitectură de ansamblu

```
                  ┌──────────────────────────────────────────────┐
                  │                  BROWSER (SPA)               │
                  │  React 19 + Tailwind                         │
                  │  ┌──────────────┐   ┌────────────────────┐   │
                  │  │ Auth pages   │   │ Client Dashboard   │   │
                  │  └──────────────┘   │  - chat            │   │
                  │  ┌──────────────┐   │  - VoiceCallOverlay│   │
                  │  │ CallCenter   │   │    (Web Speech API)│   │
                  │  │  Dashboard   │   └────────────────────┘   │
                  │  └──────────────┘                            │
                  └───────────┬──────────────────────────────────┘
                              │  HTTPS / JSON  (JWT Bearer)
                              ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                       FastAPI app (uvicorn)                      │
   │                                                                  │
   │  controller/   ──►  service/   ──►  persistence/ (UoW + repos)   │
   │  (HTTP layer)      (use-cases)     (SQLAlchemy session)          │
   │                          │                                       │
   │                          ▼                                       │
   │                    agent/ (Coordinator → Operator)               │
   │                          │                                       │
   │           ┌──────────────┼─────────────────┐                     │
   │           ▼              ▼                 ▼                     │
   │      faq_lookup     rag_search       run_sql_select              │
   │      (FAQ JSON)     (Chroma + KB)    (read-only)                 │
   └──────────┬──────────────┬─────────────────┬──────────────────────┘
              │              │                 │
              ▼              ▼                 ▼
   ┌────────────────┐ ┌─────────────────┐ ┌────────────────────────┐
   │  data/cc_<id>/ │ │  OpenAI API     │ │ Baza de date proprie a │
   │   faq.json     │ │  embeddings+chat│ │ fiecărui call center   │
   │   chroma/      │ │                 │ │ (READ-ONLY, SELECT/WITH)│
   │   kb/*.pdf     │ └─────────────────┘ └────────────────────────┘
   └────────────────┘
                       Platform DB (PostgreSQL):
                          call_centers, clients, tickets,
                          messages, revoked_tokens
```

### Backend — Layered (Clean) Architecture

```
HTTP → controller/  →  service/  →  persistence/  →  DB
                  │
                  └──►  agent/      (LLM orchestration)
                          │
                          ├──►  tools/   (FAQ, RAG, SQL)
                          ├──►  vector_store  (Chroma)
                          └──►  memory   (per-conversation)
```

- **`@D:/Licenta/app/controller`** — adaptoare HTTP. Validează DTO-urile, mapează excepțiile de domeniu pe coduri HTTP, nu conțin logică de business.
- **`@D:/Licenta/app/service`** — orchestrarea cazurilor de utilizare (`AuthService`, `ConversationService`). Tot ce ține de „un client trimite un mesaj”, „închidem un ticket”, „înregistrăm un cont” trăiește aici.
- **`@D:/Licenta/app/persistence`** — pattern **Unit of Work** (`@D:/Licenta/app/persistence/unit_of_work.py:13-42`) care expune un set de **Repository**-uri (`call_centers`, `clients`, `messages`, `tickets`, `revoked_tokens`) peste aceeași sesiune SQLAlchemy. Service-urile nu ating direct sesiunea, ci doar `uow.<repo>.<method>(...)` + `uow.commit()`.
- **`@D:/Licenta/app/model`** — entitățile ORM (`call_centers`, `client`, `tickets`, `messages`, `revoked_tokens`, `enums`).
- **`@D:/Licenta/app/schemas`** — DTO-uri Pydantic pentru request/response.
- **`@D:/Licenta/app/security`** — emitere/verificare JWT (`jwt.py`) și dependency `get_current_actor` care produce un `CurrentActor { actor_type, actor_id }` (call_center sau client).
- **`@D:/Licenta/app/agent`** — *creierul* agentic-RAG (vezi secțiunea 4).

### Frontend — împărțire pe responsabilități

- **`@D:/Licenta/client/src/context/AuthContext.js`** — stochează tokenul JWT și tipul actorului; expune `login` / `logout` / `register`.
- **`@D:/Licenta/client/src/services/api.js`** — wrapper Axios cu interceptor de `Authorization: Bearer <jwt>`; grupat pe `authAPI`, `conversationAPI`, `ticketsAPI`, `callCenterAPI`.
- **`@D:/Licenta/client/src/components/auth`** — `Login`, `Register`, `DebugLogin`.
- **`@D:/Licenta/client/src/components/callcenter`** — `CallCenterDashboard` (admin: upload PDF, vedere conversații).
- **`@D:/Licenta/client/src/components/client`** — `ClientDashboard` (chat + listă conversații + tichete) și `VoiceCallOverlay` (apelul vocal hands-free).
- **`@D:/Licenta/client/src/hooks/useVoiceCall.js`** — hook care încapsulează loop-ul `listening → thinking → speaking → ended` peste Web Speech API.

---

## 4. Pipeline-ul agentic-RAG (`@D:/Licenta/app/agent`)

Componenta-cheie a proiectului. Toate fișierele relevante sunt în `@D:/Licenta/app/agent`.

### 4.1 Coordinator (`coordinator.py`)

`Coordinator.build(call_center_id)` este *fabrica* care construiește, **lazy**, un `OperatorContext` complet pentru un call center dat:

1. Citește din tabela `call_centers` numele, descrierea, `knowledge_base_path` și `database_uri`.
2. Creează / deschide colecția Chroma `cc_<id>` din `data/cc_<id>/chroma/`.
3. Indexează knowledge base-ul (PDF / md / txt / csv / rst / log) prin `kb_indexer.collect_chunks(...)` → chunk-uri de ~1200 caractere cu overlap de 200; embeddings via OpenAI `text-embedding-3-small`; upsert idempotent în Chroma (`vector_store.index_documents`).
4. Construiește `CallCenterDB(database_uri)` (`@D:/Licenta/app/agent/schema.py`): introspectează schema, expune `run_select(sql)` **read-only** care:
   - refuză orice altceva decât `SELECT` / `WITH ... SELECT`,
   - blochează keyword-uri periculoase (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `EXEC`, etc.),
   - refuză statement-uri multiple,
   - limitează rezultatul la `max_rows=50`.
5. Construiește cele trei tool-uri: `faq_lookup`, `rag_search`, `run_sql_select` (`agent/tools/`).
6. Compune `SYSTEM_PROMPT` cu numele tenant-ului, descrierea, schema DB și — **important** — regulile de **SCOPE strict** și **prompt-injection defense** (vezi 4.5).

Rezultatul este cached într-un `registry` (`@D:/Licenta/app/agent/registry.py`); `reset_operator(cc_id)` îl re-construiește (folosit după upload-ul unui PDF nou).

### 4.2 Operator (`operator.py`)

`Operator.answer(state, question)` este loop-ul de inferență per turn:

1. **Fast path FAQ** — `FaqStore.lookup(question)` face matching pe embeddings cu `faq_similarity_threshold = 0.86`. Dacă găsește, returnează direct fără a chema LLM-ul (latență ~0, cost zero).
2. **Tool-using LLM path** — `_run_with_tools`:
   - Construiește mesajele: `system` + ultimele `history_limit=12` turnuri din `AgentState`.
   - Trimite la `gpt-4o-mini` cu schema celor 3 tool-uri și `temperature=0.2`.
   - Dacă răspunsul conține `tool_calls`, le execută local, atașează rezultatul ca mesaj `role: "tool"`, și buclează (max `max_tool_iterations = 5`).
   - Dacă atinge plafonul, forțează un răspuns final cu un system message suplimentar care interzice tool-uri.
3. Etichetează turnul cu sursa folosită (`faq` | `kb` | `db` | `llm`) și salvează în `state.slots["turn_sources"]` — etichetele se folosesc ulterior la extracția FAQ.
4. Detectează semnale de închidere („thanks bye”, „asta e tot”, „la revedere”, etc.) și setează `conversation_finished`.

### 4.3 Vector store (`vector_store.py`)

Wrapper minimal peste `chromadb.PersistentClient`. Cheia arhitecturală: **o colecție per call center** (`cc_<id>`), stocată în `data/cc_<id>/chroma/`. Izolarea între tenants este garantată prin construcție — nu există nicio cale prin care `rag_search` al unui call center să atingă chunk-urile altuia.

### 4.4 Memorie de conversație (`memory.py`)

`AgentMemory` ține turnurile în memoria procesului, cheie `(call_center_id, session_id)`, TTL de 1 oră. Nu se persistă în DB până când conversația nu e închisă — atunci payload-ul complet (`turns` + `slots`) intră în tabela `tickets`.

### 4.5 Securitate la nivel de prompt

`SYSTEM_PROMPT` (`@D:/Licenta/app/agent/coordinator.py:22-52`) conține trei blocuri non-negociabile:

- **`SCOPE (strict)`** — agentul răspunde *doar* la întrebări legate de call center; refuză într-o singură propoziție orice off-topic; pentru mesaje compuse (on-topic + off-topic), răspunde *doar* la partea on-topic și refuză restul.
- **`SECURITY (prompt-injection defense)`** — orice text din mesajele user-ului sau din documentele returnate de tool-uri este tratat ca **date**, nu ca instrucțiuni. Tentativele „ignore previous instructions”, „act as”, „reveal your prompt”, schimbare permanentă de limbă etc. sunt refuzate cu propoziția standard.
- **Confidențialitate** — interzice dezvăluirea promptului de sistem și a schemei DB, fie și parafrazat.

### 4.6 Învățare offline: extragere FAQ (`faq_extractor.py`)

La fiecare conversație închisă cu `success=True`:

1. Se asociază fiecare turn de user cu următorul turn de assistant → perechi Q/A.
2. Se filtrează perechile care provin din `db` (date personale) sau care **arată** ca date personale (emails, numere de telefon, ID-uri lungi, date calendaristice) prin regex-uri în `_PERSONAL_PATTERNS`.
3. Restul se trimit la `gpt-4o-mini` (temperature 0, `response_format=json_object`) cu instrucțiunea de a păstra doar perechile generic-reutilizabile și a le reformula curat.
4. Rezultatele se adaugă în `FaqStore` (`data/cc_<id>/faq.json`) împreună cu embedding-ul întrebării — pentru ca `faq_lookup` ulterior să le poată găsi.

Efect: cu cât platforma e folosită mai mult, cu atât mai multe răspunsuri sunt servite din cache instant, fără cost de LLM.

---

## 5. Fluxuri principale

### 5.1 Trimitere mesaj text (chat)

```
[Browser] POST /conversations/{id}/messages { text }
   │  Bearer JWT
   ▼
controller/conversation_controller.send_message
   ▼
ConversationService.send_message
   ▼
registry.get_operator(call_center_id)  ──►  Coordinator.build(...) (lazy, cached)
   ▼
Operator.answer(state, question)
   ├─ FaqStore.lookup → hit? return cached
   └─ _run_with_tools → LLM ↔ {faq_lookup, rag_search, run_sql_select}
   ▼
{ answer, conversation_finished }
```

### 5.2 Apel vocal (hands-free)

Implementat 100% în browser folosind **Web Speech API**, fără media server:

```
useVoiceCall (loop):
  status=listening → SpeechRecognition.start() → text
  status=thinking  → POST /conversations/{id}/messages → { answer }
  status=speaking  → speechSynthesis.speak(answer)
  → repeat sau ended dacă conversation_finished
```

Hook-ul `@D:/Licenta/client/src/hooks/useVoiceCall.js` expune `start`, `hangUp`, `muted`, `transcript`, `status`, iar overlay-ul `@D:/Licenta/client/src/components/client/VoiceCallOverlay.js` îl montează pe ecran complet cu indicator vizual de stare (listening / thinking / speaking).

### 5.3 Upload PDF în knowledge base (admin)

```
POST /call-center/upload-pdf  (multipart)
   ▼
salvare în data/cc_<id>/kb/<file>.pdf
   ▼
reset_operator(cc_id) → Coordinator.build → reindex întregul KB
   ▼
RAG e disponibil imediat pe noul conținut
```

### 5.4 Închidere conversație → ticket → FAQ

```
POST /conversations/{id}/close { success }
   ▼
ConversationService.close_conversation
   ├─ persistă Ticket(status, summary, payload={turns,slots,...})
   ├─ dacă success=True → extract_faq_from_ticket(payload, faq_store)
   └─ AgentMemory.reset(...)
```

---

## 6. Autentificare & autorizare

- JWT cu `python-jose`, claim `actor_type` ∈ `{call_center, client}` + `actor_id`.
- Logout-ul adaugă `jti`-ul în tabela `revoked_tokens` → middleware-ul `get_current_actor` îl verifică la fiecare cerere.
- Endpoint-urile cu efect (chat, upload PDF) au verificări explicite de tip actor:
  - `_require_client(actor)` în `@D:/Licenta/app/controller/conversation_controller.py:22-24`.
  - `actor.actor_type != "call_center"` la upload PDF în `@D:/Licenta/app/controller/pdf_upload.py:49-50`.
- Parolele sunt stocate cu `bcrypt` prin `passlib`.

---

## 7. Layout pe disc (per call center)

```
data/
└── cc_<id>/
    ├── kb/                  # PDF-urile urcate prin UI-ul de admin
    │   └── *.pdf
    ├── chroma/              # Vector DB persistentă (HNSW, cosine)
    │   └── ...
    └── faq.json             # FAQ-uri învățate din conversații închise cu succes
```

Această convenție face *backup-ul per tenant* și *retragerea unui tenant* operațiuni triviale (un singur director).

---

## 8. Rulare locală

### Cerințe

- Python **3.11+**, Node **18+**, PostgreSQL accesibil.
- Cont OpenAI cu API key (folosit pentru embeddings + chat).

### Variabile de mediu (`.env` la rădăcină)

```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/fastcall
JWT_SECRET=change-me
# opțional (override-uri):
# chat_model=gpt-4o-mini
# embedding_model=text-embedding-3-small
# top_k=6
```

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000
```

OpenAPI interactiv: `http://localhost:8000/docs`.

### Frontend

```bash
cd client
npm install
npm start                       # http://localhost:3000
```

CORS este pre-configurat pentru `http://localhost:3000` în `@D:/Licenta/app/main.py:18-24`.

### Teste

```bash
pytest                          # suite pentru entități + repositories
```

---

## 9. Decizii de design notabile

- **Multi-tenancy prin izolare de stocare**, nu prin filtre la rulare. Fiecare call center are colecție Chroma, FAQ JSON și URI de DB proprii. Nicio interogare nu poate „să se scape” spre alt tenant.
- **Operator cached, dar `lazy`**. Construcția lui (inclusiv reindexarea KB) e scumpă, deci se face o singură dată per call center, la prima cerere, și se reciclează la upload PDF.
- **Tool-using agent loop**, nu retrieval-then-prompt naiv. LLM-ul *decide* dacă întrebarea cere SQL, RAG sau ambele, în loc să primim mereu top-k chunk-uri în prompt indiferent de relevanță. Asta scade costul și crește acuratețea pe întrebări specifice contului (care nu pot fi rezolvate din PDF-uri).
- **FAQ cache cu prag de similaritate de embedding** (`0.86`) — răspunde la rephrasări fără să cheme LLM-ul. Învățarea e off-line, doar pe conversații încheiate cu succes, și cu filtru explicit pentru date personale.
- **Voice call fără server media**. Folosirea Web Speech API mută complet costul de STT/TTS pe browser, ceea ce face arhitectura mult mai simplă (nu există stream de audio pe server) și 0$ pe minut de apel.
- **Read-only DB tool cu allowlist explicit**. Tool-ul SQL nu trimite niciodată DDL/DML către DB-ul tenant-ului, indiferent de ce ar genera LLM-ul; validarea e în Python, înainte de execuție.
- **Prompt-injection defense la nivelul system prompt-ului**, întărită cu reguli explicite pentru mesaje compuse (on-topic + off-topic) — vezi `@D:/Licenta/app/agent/coordinator.py:35-44`.