# Akshara Annotation Platform

A full-stack, multi-role audio annotation platform for Hindi, English, and Telugu speech data. Annotators transcribe audio segments, reviewers approve or request corrections, and administrators manage users, datasets, pipelines, and exports through either a React or Streamlit frontend backed by a shared FastAPI + Supabase PostgreSQL backend.

---

## Architecture

```
React Frontend (Vite)          Streamlit Frontend
        |                              |
        +-----------------------------+
                       |
              FastAPI Backend (Python)
                       |
              Supabase PostgreSQL
                       |
              Supabase Storage (audio files)
```

ASR / Curation Pipelines run server-side inside the FastAPI backend:

| Language | Pipeline |
|----------|----------|
| Hindi    | AI4Bharat IndicConformer + Pyannote diarization (HF_TOKEN) |
| English  | OpenAI Whisper |
| Telugu   | AI4Bharat IndicConformer |

> SQLite is NOT supported. The backend raises a startup error if DATABASE_URL is missing or points to SQLite.

---

## Repository Structure

```
akshara-annotation-system/
+-- backend/                    # FastAPI application
|   +-- api/routers/            # Endpoint routers (auth, users, audio, annotations, curation...)
|   +-- core/
|   |   +-- config.py           # Settings loaded from environment / .env
|   |   +-- dependencies.py     # FastAPI dependency injection (auth, db, roles)
|   +-- database/
|   |   +-- database.py         # SQLAlchemy engine + session factory (PostgreSQL only)
|   |   +-- models.py           # ORM models
|   |   +-- enums.py            # UserRole, TaskStatus, etc.
|   +-- pipelines/              # ASR pipeline runners
|   |   +-- hindi_pipeline.py
|   |   +-- english_pipeline.py
|   |   +-- telugu_pipeline.py
|   |   +-- pipeline_runner.py
|   +-- schemas/                # Pydantic request/response schemas
|   +-- services/               # Business-logic layer
|   +-- utils/                  # Audio utilities, RSML parser/formatter
|   +-- main.py                 # FastAPI application entry point
|
+-- frontend/                   # React 19 + Vite application
|   +-- src/
|   |   +-- pages/              # Route-level pages (admin, annotator, reviewer)
|   |   +-- components/         # Reusable UI components
|   |   +-- services/api.ts     # Axios instance + token-refresh interceptor
|   |   +-- App.tsx             # Router + global error/maintenance handling
|   +-- package.json
|   +-- vite.config.ts
|
+-- streamlit/                  # Streamlit frontend (shares backend/DB with React)
|   +-- app.py                  # Entry point
|   +-- views/
|   |   +-- admin.py
|   |   +-- annotator.py
|   |   +-- reviewer.py
|   +-- components/             # Custom Streamlit components (WaveSurfer player)
|   +-- requirements.txt
|
+-- scripts/                    # Utility scripts (create admin, migrate data...)
+-- migrations/                 # Database migration scripts
+-- tests/                      # Backend test suite (pytest)
+-- docs/                       # Additional documentation
+-- .env.example                # Environment variable template - copy to .env
+-- .gitignore
+-- README.md
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | Backend + Streamlit |
| Node.js 18+ | React frontend |
| npm | Bundled with Node.js |
| Supabase account | Provides PostgreSQL + Storage (free tier sufficient) |
| FFmpeg | Required by ASR pipelines (must be on PATH) |
| GPU / CUDA | Recommended for Hindi and Telugu pipelines (CPU works but is slow) |
| Hugging Face token | Required for Hindi pipeline (Pyannote diarization). Must accept the Pyannote model licence on HuggingFace. |

---

## Clone

```bash
git clone https://github.com/KushalManikonda/akshara-annotation-system.git
cd akshara-annotation-system
```

---

## Environment Configuration

```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

Open `.env` and fill in every variable:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `JWT_SECRET_KEY` | Random string >= 32 chars. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CORS_ORIGINS` | Comma-separated allowed origins (include your React dev URL) |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Public anon key (safe for client-side) |
| `SUPABASE_SERVICE_KEY` | Service-role secret - NEVER expose to frontend |
| `STORAGE_BUCKET` | Supabase Storage bucket name (default: `audio-files`) |
| `HF_TOKEN` | Hugging Face token - required for Hindi pipeline only |
| `WHISPER_MODEL_PATH` | HF model ID or local path (default: `openai/whisper-base`) |
| `INDIC_CONFORMER_MODEL` | HF model ID (default: `ai4bharat/indic-conformer-600m-multilingual`) |
| `PIPELINE_TEMP_DIR` | Writable temp directory for intermediate pipeline files |

> NEVER commit your real `.env`. It is already in `.gitignore`. Only `.env.example` (empty values) is committed.

---

## Supabase PostgreSQL Setup

This project is PostgreSQL / Supabase only. SQLite is explicitly rejected at startup.

1. Create a Supabase project at https://supabase.com
2. Go to **Settings > Database > Connection string > URI** and copy the full PostgreSQL URI.
   Format: `postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres`
3. Set `DATABASE_URL` in your `.env` to that URI.
4. Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_KEY` from **Settings > API**.
5. Create a Storage bucket named `audio-files` (or the name you set in `STORAGE_BUCKET`).
6. The backend automatically creates all required tables (via SQLAlchemy `create_all`) on first startup.

---

## Backend Setup

```bash
# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the backend (loads .env automatically via python-dotenv)
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/api/docs

---

## React Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The React app runs at http://localhost:5173 and proxies `/api/*` requests to the backend on port 8000 (configured in `vite.config.ts`).

For production builds, set `VITE_API_BASE_URL` in `frontend/.env.local` to your deployed backend URL.

---

## Streamlit Setup

Streamlit uses the same FastAPI backend and Supabase database as React.

```bash
# Activate your Python virtual environment first
pip install -r streamlit/requirements.txt

streamlit run streamlit/app.py
```

Streamlit is available at http://localhost:8501

---

## Running the Full System

Open three terminals from the project root:

**Terminal 1 - Backend**
```bash
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - React Frontend**
```bash
cd frontend && npm run dev
```

**Terminal 3 - Streamlit (optional)**
```bash
streamlit run streamlit/app.py
```

| Service | URL |
|---------|-----|
| React UI | http://localhost:5173 |
| Streamlit UI | http://localhost:8501 |
| FastAPI | http://127.0.0.1:8000 |
| API Docs | http://127.0.0.1:8000/api/docs |

---

## Roles

| Role | Responsibilities |
|------|----------------|
| **Admin** | Manages users, uploads datasets, monitors progress, runs ASR curation pipelines, exports finalized annotations, controls system settings (Maintenance Mode). |
| **Annotator** | Receives assigned audio tasks, edits the ASR-generated transcript using RSML tags, and submits for review. |
| **Reviewer** | Inspects submitted annotations, approves them or sends them back with written feedback. |

---

## Core Workflow

```
Admin uploads audio file
        |
Language selected (Hindi / English / Telugu)
        |
ASR curation pipeline runs (IndicConformer / Whisper)
        |
Transcript JSON stored in PostgreSQL
        |
Task assigned to Annotator
        |
Annotator edits transcript in waveform editor -> submits
        |
Reviewer inspects -> approves or requests revision
        |
On approval: audio status -> COMPLETED
        |
Admin exports: original audio + transcript JSON + annotated SRT
```

---

## ASR Curation Pipelines

Invoked from the **Curation** section of the Admin dashboard.

### Hindi Pipeline
- ASR: AI4Bharat `indic-conformer-600m-multilingual`
- Diarization: Pyannote (requires `HF_TOKEN` + model licence accepted on HuggingFace)
- Source separation: Demucs (vocals extraction before ASR)

### English Pipeline
- ASR: OpenAI Whisper (`openai/whisper-base` or configured model)
- No separate diarization step

### Telugu Pipeline
- ASR: AI4Bharat `indic-conformer-600m-multilingual`
- No separate diarization step

---

## Exports

Once an annotation is approved, admins can export from the **Exports** section.

Each export ZIP contains:
- `original_audio.<ext>` - the original uploaded audio (from Supabase Storage)
- `original_transcript.json` - the raw ASR transcript JSON
- `annotated_transcript.srt` - the final annotated transcript in SRT subtitle format

---

## Development Guidelines

- Never commit secrets. `.env` is in `.gitignore`. Use `.env.example` for documentation.
- Never hardcode machine-specific paths. Use `pathlib.Path`, `os.environ`, and the `settings` object.
- Never introduce SQLite. The backend explicitly rejects it at startup.
- Preserve role/auth behaviour. Changes to `dependencies.py` affect all protected routes.
- Keep React and Streamlit aligned. If you change shared backend API behaviour, update both frontends.
- Do not commit generated files. ZIPs, `.pyc`, `node_modules`, `dist/`, model caches, and audio uploads are all gitignored.

---

## Deployment (Render)

This project targets [Render](https://render.com) for deployment.

### Recommended Render Architecture

| Render Service | Type | Content |
|---------------|------|---------|
| `akshara-api` | Web Service | FastAPI backend |
| `akshara-frontend` | Static Site | React build |
| `akshara-streamlit` | Web Service (optional) | Streamlit |
| Supabase | External | PostgreSQL + Storage |

### FastAPI Web Service
- Build: `pip install -r requirements.txt`
- Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

### React Static Site
- Build: `cd frontend && npm install && npm run build`
- Publish directory: `frontend/dist`
- Set `VITE_API_BASE_URL` env var to your FastAPI Render URL.

### Streamlit Web Service
- Build: `pip install -r streamlit/requirements.txt`
- Start: `streamlit run streamlit/app.py --server.port $PORT --server.address 0.0.0.0`

### Environment Variables on Render
Set `DATABASE_URL`, `JWT_SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `CORS_ORIGINS`, `HF_TOKEN`, and all other variables in each Render service's **Environment** tab. Never paste real credentials into source files.

> Pipeline note: Hindi and Telugu pipelines download large models (~1-2 GB). A paid Render instance with at least 2 GB RAM is recommended.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `CRITICAL: DATABASE_URL is not set` | `.env` missing | Copy `.env.example` to `.env` and fill in `DATABASE_URL` |
| `CRITICAL: SQLite is no longer supported` | Wrong connection string | Use Supabase PostgreSQL URI |
| Supabase connection refused | Wrong credentials | Verify `DATABASE_URL` in Supabase dashboard |
| React "Failed to fetch" | Backend not running | Start uvicorn on port 8000 |
| CORS error in browser | Origin not in `CORS_ORIGINS` | Add your frontend URL to `CORS_ORIGINS` |
| Hindi pipeline fails | `HF_TOKEN` missing or licence not accepted | Set `HF_TOKEN`; accept Pyannote licence at huggingface.co |
| `ffmpeg not found` | FFmpeg not installed | Install FFmpeg and add to PATH |
| `npm install` fails | Node.js version too old | Upgrade to Node.js 18+ |
| `pip install` fails | Python version too old | Use Python 3.10+ |

---

## Contributing

1. Fork this repository on GitHub.
2. Clone your fork: `git clone https://github.com/<your-username>/akshara-annotation-system.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make changes following the Development Guidelines.
5. Test with `pytest tests/` and verify both React and Streamlit UIs.
6. Commit: `git commit -m "feat: describe your change"`
7. Push: `git push origin feature/your-feature-name`
8. Open a Pull Request against the `main` branch.

---

## License

MIT - see [LICENSE](LICENSE).
