# AI Travel Planner

**A hackathon-ready, AI-powered travel itinerary generator.** Build day-by-day plans with hotels, meals, and sightseeing—then refine them in natural language. Built for the **DigitalOcean Gradient AI Hackathon**.

![AI Travel Planner](https://img.shields.io/badge/AI-Travel%20Planner-16a34a?style=flat)
![FastAPI](https://img.shields.io/badge/FastAPI-1.0-009688?style=flat)
![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat)

---

## Features

- **AI-generated itineraries** — Hotels, breakfast/lunch/dinner, and sightseeing for every day
- **Smart budget planning** — Per-category breakdown (accommodation, meals, activities) and budget-aware suggestions
- **Conversational refinement** — “Make it cheaper”, “Add more culture”, “Less walking” via a single instruction
- **Day difficulty** — Each day tagged as easy / moderate / intense
- **Travel tips** — Short, practical tips (e.g. “Book teamLab in advance”)
- **Local gems & crowd avoidance** — Prompts encourage hidden spots and smarter timing
- **Google Maps links** — Every place links to Maps
- **Shareable itineraries** — Copy a link to share your plan (state encoded in URL)
- **Demo mode** — One-click example prompts for Tokyo, Paris, Bali
- **Production-ready** — Logging, retries, rate limiting, caching, health check, Docker

---

## Project structure

```
.
├── app/
│   ├── main.py              # FastAPI app, CORS, static serving, error handling
│   ├── config.py            # Pydantic settings, env validation
│   ├── models.py            # Request/response models (incl. Refine, BudgetBreakdown)
│   ├── routers/
│   │   ├── health.py        # GET /v1/health, GET /v1/demo-prompts
│   │   └── itinerary.py     # POST /v1/itinerary/, POST /v1/itinerary/refine
│   └── services/
│       ├── cache.py         # In-memory TTL cache for responses
│       ├── llm_service.py   # OpenAI client, retry, fallback, prompts
│       └── rate_limit.py    # Per-IP rate limiting
├── frontend/
│   └── index.html           # Single-page UI (form, results, refine, share, demo)
├── docs/
│   ├── HACKATHON_CHECKLIST.md
│   ├── TODO.md
│   └── DEPLOY.md
├── .do/
│   └── app.yaml             # DigitalOcean App Platform spec (optional)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Architecture (high level)

```
┌─────────────┐     POST /v1/itinerary/      ┌──────────────┐
│   Browser   │ ───────────────────────────► │   FastAPI    │
│  (frontend) │                               │   (backend)  │
│             │ ◄───────────────────────────  │              │
└─────────────┘     JSON itinerary            │  - Rate limit │
       │                                     │  - Cache     │
       │ GET /v1/demo-prompts                │  - LLM call   │
       │ POST /v1/itinerary/refine           └───────┬──────┘
       │                                            │
       │                                            ▼
       │                                     ┌──────────────┐
       │                                     │ OpenAI (or   │
       └─────────────────────────────────────│ compatible) │
                                             └──────────────┘
```

---

## Quick start

### 1. Clone and venv

```bash
git clone <your-repo-url>
cd ai-travel-planner
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API key

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-... (or GitHub PAT / other provider)
```

### 4. Run

```bash
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** for the UI.  
- **API docs**: http://127.0.0.1:8000/docs  
- **Health**: http://127.0.0.1:8000/v1/health  

---

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | Health check (status, version, llm_configured) |
| GET | `/v1/demo-prompts` | Example prompts for demo |
| POST | `/v1/itinerary/` | Generate itinerary (body: city, start_date, end_date, budget, preferences?) |
| POST | `/v1/itinerary/refine` | Refine itinerary (body: previous_itinerary, instruction) |

**Backward compatibility**: `POST /itinerary/` still works (same as `/v1/itinerary/`).

### Example: generate itinerary

```bash
curl -X POST http://127.0.0.1:8000/v1/itinerary/ \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Tokyo",
    "start_date": "2026-04-01",
    "end_date": "2026-04-03",
    "budget": 800,
    "preferences": "I love ramen and want to visit teamLab"
  }'
```

### Example: refine itinerary

```bash
curl -X POST http://127.0.0.1:8000/v1/itinerary/refine \
  -H "Content-Type: application/json" \
  -d '{"previous_itinerary": <full itinerary JSON>, "instruction": "make it cheaper"}'
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(required for generate/refine)* | OpenAI key or compatible provider key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name |
| `OPENAI_BASE_URL` | — | Override for GitHub Models / self-hosted |
| `OPENAI_FALLBACK_MODEL` | `gpt-4o-mini` | Fallback after retries |
| `LLM_TIMEOUT_SECONDS` | 120 | Timeout for LLM call |
| `LLM_MAX_RETRIES` | 2 | Retries on failure |
| `CACHE_TTL_SECONDS` | 300 | Cache TTL for identical requests |
| `RATE_LIMIT_REQUESTS` | 20 | Requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | 60 | Rate limit window |
| `LOG_LEVEL` | INFO | Logging level |
| `APP_ENV` | development | e.g. production |

---

## Deploy on DigitalOcean

Use **App Platform** (managed app hosting from your repo).

### 1. Push this repo to GitHub

Ensure the repo is on GitHub (public or private).

### 2. Create an App in DigitalOcean

1. In the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), click **Create** → **Apps** (or **App Platform**).
2. Choose **GitHub** as the source and **authorize** if needed.
3. Select **this repository** and the branch to deploy (e.g. `main`).
4. **Build settings**
   - **Source**: Repository (already selected).
   - **Build type**: Dockerfile.
   - **Dockerfile path**: `./Dockerfile` (default).
5. **Run settings**
   - **HTTP port**: `8080`.
   - **Health check path** (optional): `/v1/health`.
6. **Environment variables**
   - Add **OPENAI_API_KEY** (required): your OpenAI API key (or Gradient AI / other compatible key). Mark it **Encrypted**.
   - Optional: `APP_ENV` = `production`.
7. Choose a plan (e.g. Basic) and click **Create Resources** / **Deploy**.

Your app will be available at `https://<your-app>.ondigitalocean.app`.

### Using Gradient AI as the LLM

If you use **DigitalOcean Gradient AI** for the model:

- In App Platform env vars set **OPENAI_BASE_URL** to your Gradient AI endpoint (e.g. from the Gradient AI dashboard).
- Set **OPENAI_API_KEY** to your Gradient AI API key.
- Set **OPENAI_MODEL** to the model name your endpoint uses.

### App spec in repo (optional)

The repo includes `.do/app.yaml` so you can deploy via **doctl** or **Import app spec**. Edit `.do/app.yaml` and replace `YOUR_GITHUB_USERNAME/ai-travel-planner` with your GitHub repo (e.g. `johndoe/ai-travel-planner`), then create the app from that spec. You still must set **OPENAI_API_KEY** in the App Platform dashboard (Settings → App-Level Environment Variables).

---

## Deployment (other)

- **Droplet**: On a server, clone the repo, set `.env` with `OPENAI_API_KEY`, then run `docker compose up -d --build`.

---

## Screenshots

_Add 1–2 screenshots of the UI (form + itinerary result) here for the README and submission._

---

## Demo video

_Record a short demo (2–3 min) showing:_

1. Opening the app and using a **demo prompt** (e.g. Tokyo 3 days).
2. **Generating** an itinerary and scrolling through days (hotels, meals, sightseeing, budget breakdown, tips).
3. **Refining** with “make it cheaper” or “add more cultural experiences”.
4. **Sharing** via “Share itinerary” and opening the link in a new tab.

_Upload to YouTube or similar and link here._

---

## Requirements

- Python 3.11+
- See `requirements.txt` for packages (FastAPI, Uvicorn, OpenAI, Pydantic, pydantic-settings, etc.)

---

## License

MIT (or your chosen license). Ensure the repo is public and the license file is in the repo for the hackathon.
