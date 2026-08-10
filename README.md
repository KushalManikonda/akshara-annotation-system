# Akshara RSML Studio

> **Live Application**: [https://akshara-annotation-platform.streamlit.app/](https://akshara-annotation-platform.streamlit.app/)

Akshara RSML Studio is a professional audio annotation platform designed for **Rich Speech Markup Language (RSML)**. Built with Streamlit and a custom WaveSurfer.js v7 component, it provides an end-to-end workflow for annotators, reviewers, and administrators to collaboratively transcribe and review spoken audio with precision.

---

## Table of Contents

- [Live Demo](#live-demo)
- [Features Overview](#features-overview)
- [Setup from Scratch](#setup-from-scratch)
- [Directory Structure](#directory-structure)
- [Role-Based Functionality](#role-based-functionality)
  - [Annotator](#annotator)
  - [Reviewer](#reviewer)
  - [Admin](#admin)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Technical Architecture](#technical-architecture)

---

## Live Demo

Access the live deployment directly — no installation required:

🔗 **[https://akshara-annotation-platform.streamlit.app/](https://akshara-annotation-platform.streamlit.app/)**

---

## Features Overview

- **Interactive Audio Waveform** powered by WaveSurfer.js v7 with zoom, speed control, and visual region highlights
- **Draggable & Resizable Regions** — adjust segment boundaries directly on the waveform
- **Bi-directional Sync** — clicking a segment card seeks audio; clicking a region highlights the card
- **RSML Tag Autocomplete** — type `@` in any transcript field for instant tag suggestions
- **Live Normalized Preview** — side-by-side view of raw RSML input and the cleaned normalized output
- **Segment Completion Tracking** — mark segments as Done; completed segments lock the transcript to prevent accidental edits
- **Undo / Redo / Revert** — full history support for all region and transcript changes
- **Role-based Workflows** — Annotator → Reviewer → Admin pipeline with feedback loops

---

## Setup from Scratch (React + FastAPI)

Since we are actively migrating the platform to a modern React + FastAPI architecture, the process for running the application has changed from the original Streamlit instructions.

To run the new application, you will need to start both the backend server and the frontend server in two separate terminal windows.

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- A terminal (PowerShell on Windows, Terminal on macOS/Linux)

### 1. Start the Backend (FastAPI)
Open a terminal in the root directory (`Akshara-Annotation-Platform-main`) and start the backend using Uvicorn. Since we are using Supabase for the database, you'll need to pass the `DATABASE_URL` environment variable:

**On Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

$env:DATABASE_URL="postgresql://postgres:M1voma!23db@db.dqwhdmmmtpienottmlwi.supabase.co:5432/postgres"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql://postgres:M1voma!23db@db.dqwhdmmmtpienottmlwi.supabase.co:5432/postgres"
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
*(Note: The backend runs on `http://127.0.0.1:8000`)*

### 2. Start the Frontend (React + Vite)
Open a **second** terminal, navigate to the `frontend` folder, and start the Vite development server:

```powershell
cd frontend
npm install   # Run this once if you haven't already installed dependencies
npm run dev
```

*(Note: The frontend will be available at `http://localhost:5173`)*

Once both are running, open `http://localhost:5173` in your browser. The frontend will automatically route API requests to your local backend on port 8000.

---

## Directory Structure

```
Akshara-Annotation-Platform/
├── app.py                          # Main Streamlit entry point
├── requirements.txt                # Python dependencies
│
├── views/                          # Page-level UI views
│   ├── annotator.py                # Annotator dashboard
│   ├── reviewer.py                 # Reviewer dashboard
│   └── admin.py                   # Admin dashboard
│
├── components/                     # Custom UI components
│   └── annotator/
│       ├── wavesurfer_editor.py    # Streamlit component wrapper
│       └── wavesurfer_custom/
│           └── index.html          # Core HTML/JS WaveSurfer player
│
├── database/                       # Database models & setup
│   ├── models.py                   # SQLAlchemy ORM models
│   └── db.py                      # Database session & engine
│
├── services/                       # Business logic layer
│   ├── task_service.py             # Task assignment & status management
│   └── annotation_service.py      # Annotation CRUD operations
│
└── scripts/                        # Utility scripts
    ├── setup_db.py                 # Database initialization & seeding
    └── generate_sample_data.py     # Creates sample audio tasks
```

---

## Role-Based Functionality

### Annotator

Annotators are responsible for transcribing audio segments into RSML format.

**Dashboard**
- View the personal task queue showing assigned audio files
- See task status: Pending, In Progress, Submitted, Approved, or Needs Revision
- Click **Back to Queue** at any time to return to the task list without losing progress

**Audio Player**
- Full waveform visualization with zoom and playback speed control
- Click anywhere on the waveform to seek to that position
- Use the scrollbar below the waveform to navigate long audio files
- Double-click a region on the waveform to play only that segment (auto-stops at the end)

**Segment Management**
- Each audio segment appears as a colored region on the waveform and as a card on the right panel
- **Drag** a region to move it; **resize the edges** to adjust start/end times
- **Split Segment** (✂ icon): places the playback cursor inside a segment, then click cut to split it at that exact point
- **Delete Segment** (🗑 icon): removes the segment from both waveform and transcript panel
- **Add Segment** button: adds a new 2-second segment starting at the current playback position
- Timestamp inputs (start/end) in each card are directly editable

**Transcript Editing**
- Each segment card has an **Editable ASR Transcript** field on the left and a live **Normalized Preview** on the right
- Type `@` to trigger autocomplete for RSML tags (e.g., `@breathe`, `@laughter`, `@umm`)
- The normalized preview updates live as you type
- **Done Checkbox**: tick this when you finish a segment. This locks the transcript to prevent accidental edits. Untick to unlock and edit again.
- Locked (completed) segments are highlighted with a green left border

**History Controls**
- **Ctrl+Z**: Undo the last change (region move, edit, split, delete, add)
- **Ctrl+Y**: Redo the last undone change
- **Revert** button: instantly resets all segments back to the original state when the task was first loaded

**Saving**
- **Save Changes** button: manually saves all current segment data to the backend
- Changes are also auto-saved whenever you check/uncheck the Done checkbox or edit timestamps
- When finished with all segments, click **Submit** to send the task to reviewers

---

### Reviewer

Reviewers inspect submitted annotations and either approve them or send them back with feedback.

**Dashboard**
- View a queue of tasks submitted by annotators awaiting review
- Filter tasks by status, speaker, or submission date

**Review Interface**
- Opens the same audio player with the annotator's completed transcript loaded
- Navigate through each segment, listening to the audio and comparing it with the transcript
- Segments are read-only in review mode to prevent accidental changes

**Actions**
- **Approve**: marks the task as complete and moves it to the approved pool
- **Reject / Request Revision**: sends the task back to the annotator with a written comment explaining what needs to be fixed
- The annotator receives the feedback in their queue and can re-edit and re-submit

---

### Admin

Admins have full control over the platform and all users' work.

**User Management**
- Create, edit, and deactivate user accounts
- Assign roles: Annotator, Reviewer, or Admin
- Reset passwords

**Task Management**
- Upload new audio files and create annotation tasks
- Assign tasks to specific annotators or leave them in a shared pool
- Monitor task progress across all users in real time

**Dashboard & Analytics**
- View platform-wide statistics: total tasks, completion rate, tasks pending review
- Identify bottlenecks (e.g., tasks stuck in a particular status for too long)
- Export annotation data in JSON or CSV format for downstream processing

**Quality Control**
- Override any reviewer decision
- Reassign tasks between annotators or reviewers
- View the full edit history of any task

---

## Keyboard Shortcuts

These shortcuts work anywhere in the annotator view when focus is not inside a text field:

| Shortcut | Action |
|----------|--------|
| `Space` | Play / Pause audio |
| `←` | Rewind 10 seconds |
| `→` | Forward 10 seconds |
| `Shift + ←` | Go to Previous Task |
| `Shift + →` | Go to Next Task |
| `Ctrl + Z` | Undo last action |
| `Ctrl + Y` | Redo last undone action |
| `Ctrl + D` | Duplicate active segment |

---

## Technical Architecture

| Layer | Technology |
|-------|------------|
| Frontend UI | Streamlit (Python) |
| Audio Player | WaveSurfer.js v7 + Regions Plugin |
| Tag Autocomplete | Tribute.js |
| Component Bridge | Streamlit Custom Component API (`postMessage`) |
| Database | SQLite via SQLAlchemy ORM |
| Deployment | Streamlit Community Cloud |

The audio player is a fully self-contained HTML/JS component embedded inside Streamlit via an `<iframe>`. It communicates bidirectionally with the Python backend using `window.parent.postMessage` (component → Streamlit) and the `streamlit:render` message event (Streamlit → component). The audio file itself is **never modified** — only the region metadata (start time, end time, speaker, transcript) is read and written.
