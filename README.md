# Intelligent Historical Knowledge Archive

A production-ready platform for scalable multi-format document ingestion, AI-powered processing, entity relation knowledge graph synthesis, and hybrid neural/vector retrieval.

---

## 🏛️ System Architecture

The system is structured as a decoupled multi-layered architecture:

- **Frontend**: Next.js 14 (App Router) + TypeScript + Custom Glassmorphism UI
- **Backend API**: FastAPI + Pydantic v2 + Dependency Injection
- **Database & Storage**: PostgreSQL 16 + `pgvector` extension + SQLAlchemy 2.0 (Async) + Alembic
- **Object Storage Abstraction**: Pluggable storage engine (Local zero-copy streaming & AWS S3 adapter interface)
- **AI & Embedding Engine**: Pluggable AI / Embeddings provider interface with Gemini, Sentence-Transformers, and Mock modes

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Docker & Docker Compose (or local PostgreSQL 16 with pgvector)

### 2. Environment Configuration

Copy the example configuration file:

```bash
cp .env.example .env
```

Ensure the database connection string is properly configured in `.env`:
```ini
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/historical_archive"
DATABASE_SYNC_URL="postgresql://postgres:postgres@localhost:5432/historical_archive"
STORAGE_BACKEND="local"
STORAGE_LOCAL_DIR="./storage/data"
```

---

## 🐳 Running with Docker Compose

To launch the full stack (PostgreSQL with pgvector, FastAPI Backend, and Next.js Frontend):

```bash
docker-compose up --build
```

- **Frontend Console**: [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Swagger**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **Backend Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 💻 Local Development Setup

### Backend

1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Run Database Migrations:
   ```bash
   alembic upgrade head
   ```

4. Start the FastAPI Development Server:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

### Frontend

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start Next.js Development Server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Testing

Execute the comprehensive test suite using `pytest`:

```bash
pytest -v
```

Test coverage includes:
- System settings and dynamic CORS parsing
- Object storage abstraction (streaming, SHA-256 validation, path traversal security)
- Database entity models and relational constraints
- pgvector vector dimension validation (384-dim)
- Alembic migration discovery and head validation
- FastAPI root, ping, and health probe API contracts

---

## 📂 Project Structure

```
├── .env.example                # Example environment configuration
├── .gitignore                  # Global git ignore configuration
├── alembic.ini                 # Alembic database migration configuration
├── docker-compose.yml          # Container orchestration (PostgreSQL+pgvector, API, UI)
├── pytest.ini                  # Pytest configuration
├── README.md                   # Project documentation
├── backend/
│   ├── Dockerfile              # Backend container definition
│   ├── requirements.txt        # Python backend dependencies
│   └── app/
│       ├── main.py             # FastAPI entrypoint, lifespan, CORS, and routing
│       ├── api/                # API endpoints and dependency injection (deps.py)
│       ├── core/               # Configuration (config.py), database engine, logging
│       ├── models/             # SQLAlchemy ORM models (pgvector, documents, entities)
│       ├── schemas/            # Pydantic schemas
│       └── services/           # Business services (Ingestion, Processing, Search)
├── database/
│   └── migrations/             # Alembic migration scripts and versions
├── frontend/
│   ├── Dockerfile              # Frontend multi-stage container definition
│   ├── package.json            # Next.js & React dependencies
│   ├── tsconfig.json           # TypeScript configuration
│   ├── app/                    # Next.js App Router (layout, page, styles)
│   ├── components/             # Reusable UI components (StatusDashboard, etc.)
│   └── lib/                    # API client and type definitions
├── storage/                    # Object storage provider abstractions
└── tests/                      # Pytest unit and integration test suite
```
