# Akshara Annotation Platform

A full-stack audio annotation platform for Hindi, English, and Telugu speech data. Annotators transcribe audio segments, reviewers approve or request corrections, and administrators manage users, datasets, pipelines, and exports.

Built with React (Vite) on the frontend and FastAPI + Supabase (PostgreSQL & Storage) on the backend.

---

## Architecture

- **Frontend**: React 19 + Vite, running on Vercel or standard static hosting.
- **Backend**: FastAPI (Python), running on Render or any ASGI server.
- **Database**: Supabase PostgreSQL.
- **Storage**: Supabase Storage for storing audio files securely.

---

## Deployment (Render & Vercel)

This system is designed to be easily deployed using Render (for the backend) and Vercel (for the frontend).

### Step 1: Deploy Backend to Render
1. Create a **New Web Service** in Render and connect your GitHub repository.
2. Build Command: `pip install -r backend/requirements.txt`
3. Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Provide the following Environment Variables:
   - `ENVIRONMENT` = `production`
   - `DATABASE_URL` = (Your Supabase connection string)
   - `JWT_SECRET_KEY` = (A secure random string)
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`
   - `STORAGE_BUCKET` = `audio-files`
   - `CORS_ORIGINS` = (Leave empty or set to `*` until Vercel is deployed, then update to the Vercel URL)

### Step 2: Deploy Frontend to Vercel
1. Import the repository into Vercel.
2. Vercel should auto-detect Vite. Ensure Root Directory is set to `frontend`.
3. Build Command: `npm run build`
4. Set Environment Variables:
   - `VITE_API_BASE_URL` = (The URL of your Render backend, e.g., `https://akshara-backend.onrender.com`)
5. Once deployed, take the Vercel URL and add it to the `CORS_ORIGINS` in your Render backend settings.

---

## Local Development Setup

### 1. Supabase (Database & Storage)
1. Create a Supabase project at [supabase.com](https://supabase.com).
2. Get your **Database URI** (PostgreSQL) and **API keys** (Anon & Service Role).
3. Create a public storage bucket named `audio-files`.

### 2. Backend (FastAPI)
```bash
python -m venv .venv
# Activate virtual environment (.venv\Scripts\activate on Windows, source .venv/bin/activate on Mac/Linux)
pip install -r backend/requirements.txt

# Copy the example env file and fill in your Supabase credentials
cp .env.example .env

# Run the backend
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
The API runs at `http://127.0.0.1:8000` (docs at `/api/docs`).

### 3. Frontend (React)
```bash
cd frontend
npm install
npm run dev
```
The frontend runs at `http://localhost:5173`.

---

## Core Roles

- **Admin**: Upload datasets, trigger ASR curation pipelines, monitor progress, and export finalized annotations (ZIP containing original audio, raw JSON, and SRT subtitle file).
- **Annotator**: Receives assigned audio tasks, edits the ASR-generated transcript using RSML tags, and submits for review.
- **Reviewer**: Inspects submitted annotations, approves them, or sends them back to the annotator with written feedback.

---

## License

MIT - see [LICENSE](LICENSE).
