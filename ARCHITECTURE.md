# Akshara – Architecture & Foundation Documentation

**Version:** 1.0

**Project Status:** Phases 0–7 & 9 Complete (Phase 8 next)

---

# Project Overview

Akshara is a multilingual speech annotation platform developed using Streamlit for creating, managing, annotating, and reviewing speech datasets.

The application follows a layered architecture with a clear separation between the user interface, business logic, and database operations.

The goal of the project is to provide a stable, maintainable, and extensible platform for future speech annotation and linguistic research.

---

# Technology Stack

## Language

- Python 3.12

## Frontend

- Streamlit

## Backend

- Python Services

## ORM

- SQLAlchemy

## Database

- SQLite

## Utilities

- bcrypt / password hashing
- Logging
- Validation utilities

No additional frameworks should be introduced unless absolutely necessary.

---

# Architecture

```
                Streamlit UI
                      │
                Views (pages)
                      │
                Service Layer
                      │
                 SQLAlchemy ORM
                      │
                   SQLite DB
```

Each layer has a single responsibility.

---

# Folder Structure

```
project/
│
├── app.py
├── config.py
│
├── assets/
│
├── components/
│
├── database/
│
├── services/
│
├── utils/
│
├── views/
│
└── scripts/
```

This structure is considered stable.

Avoid unnecessary restructuring.

---

# Layer Responsibilities

## Views

Responsible for:

- Streamlit UI
- Forms
- Buttons
- Displaying data
- Calling services

Views MUST NOT:

- execute SQL
- manipulate database sessions
- contain business logic

---

## Services

Responsible for:

- Business logic
- Validation
- Database operations
- Transactions

Services MUST NOT:

- import Streamlit
- render UI
- depend on Views

---

## Database

Responsible for:

- Models
- Relationships
- Database initialization
- Session creation

Database layer MUST NOT:

- contain UI logic

---

## Utilities

Responsible for:

- Logging
- Validation
- RSML utilities
- Common helper functions

Utilities should remain independent of UI.

---

# Coding Rules

## Rule 1

Views never directly access the database.

Correct:

View → Service → Database

Incorrect:

View → Database

---

## Rule 2

Services never import Streamlit.

---

## Rule 3

Business logic belongs only inside services.

---

## Rule 4

Configuration values must come from config.py.

Avoid hardcoded paths or magic strings.

---

## Rule 5

Logging should use the centralized logger.

Avoid print().

---

## Rule 6

Validation should reuse utility functions whenever possible.

---

## Rule 7

Every database write operation must support rollback on failure.

---

## Rule 8

Exception handling should never silently swallow errors.

Errors should be logged.

---

## Rule 9

Do not duplicate business logic.

If the same logic appears twice, move it into a service or utility.

---

## Rule 10

Preserve backward compatibility whenever possible.

Avoid changing public service interfaces unless absolutely necessary.

---

# Current Database Modules

Implemented models include:

- User
- Dataset
- AudioFile
- Annotation
- AnnotationVersion
- ReviewComment
- ReviewerApproval
- AuditLog

Relationships should remain normalized.

---

# Current Services

Implemented:

- auth_service
- user_service
- audio_service
- assignment_service
- annotation_service
- reviewer_service

Each service owns its own domain.

Avoid mixing responsibilities.

---

# Current Project Status

## Phase 0

Planning & Architecture

Status:

✅ Complete

---

## Phase 1

Project Foundation

Status:

✅ Complete

---

## Phase 2

Authentication & User Management

Status:

✅ Complete

---

## Phase 3

Dataset Management

Status:

✅ Complete

---

## Phase 4

Assignment Management

Status:

✅ Complete

Foundation is considered frozen.

Only bug fixes should be made to these phases.

---

# Future Development Roadmap

Phase 5

Annotator Workspace

Goals:

- Audio playback
- Transcript editor
- RSML editor (TextArea implemented, validation coming in Phase 8)
- Draft saving
- Submission workflow

Status:
✅ Complete

---

Phase 6

Reviewer Workspace

Goals:

- Review queue
- Comparison
- Comments
- Approval
- Rejection

Status:
✅ Complete

---

Phase 7

Version Management

Goals:

- Annotation history
- Restore versions
- Version comparison

Status:
✅ Complete

---

Phase 8

RSML Integration

Goals:

- Live validation
- Formatting
- Error highlighting

---

Phase 9

Analytics

Goals:

- Progress dashboard
- User statistics
- Dataset statistics
- Reports (Leaderboards)

Status:
✅ Complete

---

Phase 10

Audit & Monitoring

Goals:

- Activity logs
- Search logs
- Review history

---

Phase 11

UI/UX Improvements

Goals:

- Better layouts
- Improved navigation
- Dialogs
- Responsive interface

---

Phase 12

Testing

Goals:

- Unit testing
- Integration testing
- Regression testing

---

Phase 13

Deployment

Goals:

- PostgreSQL
- Docker
- Cloud deployment
- Monitoring

---

# Development Principles

When implementing new features:

1. Preserve existing functionality.

2. Avoid unnecessary refactoring.

3. Keep changes localized.

4. Prefer small, incremental improvements.

5. Maintain clear separation of concerns.

6. Prioritize correctness over optimization.

7. Build features only after the underlying layer is stable.

---

# Foundation Freeze

The following components are considered stable and should only receive bug fixes unless a future feature explicitly requires modification:

- Authentication
- User Management
- Dataset Management
- Assignment Management
- Database Models
- Folder Structure
- Service Layer
- Configuration
- Logging
- Validation Utilities

Future development should build on top of this foundation rather than redesign it.

---

# Project Vision

Akshara aims to become a reliable, modular, and maintainable multilingual speech annotation platform that supports scalable annotation workflows while remaining simple enough to understand, extend, and maintain.

The architecture prioritizes clarity, stability, and incremental growth over unnecessary complexity.