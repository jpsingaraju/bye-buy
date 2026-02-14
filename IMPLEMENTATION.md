# Bye-Buy Implementation Status

## Overview
Multi-platform listing automation service that allows users to upload product listings, automatically post them to Facebook Marketplace, and auto-respond to buyer messages on Messenger using AI.

## Tech Stack
- **Frontend**: Next.js 16, React 19, Tailwind CSS, SWR, react-dropzone
- **Backend**: Two FastAPI services (Python 3.13+), SQLAlchemy, aiosqlite
- **Browser Automation**: Browserbase Stagehand (posting + message monitoring)
- **AI**: OpenAI GPT (auto-responder)
- **Database**: SQLite (shared, WAL mode)
- **Image Storage**: Local filesystem

---

## Architecture

Two independent FastAPI services sharing one SQLite database (`bye_buy.db` at backend root):

| Service | Port | Purpose |
|---|---|---|
| **Posting** | 8000 | Listing CRUD, image uploads, Facebook Marketplace posting via Stagehand |
| **Messaging** | 8001 | Monitors Messenger conversations, auto-responds to buyers via GPT |

Both services read from a single `.env` file at the backend root.

---

## Implementation Status

### Phase 1: Database & Models ✅ COMPLETE
- [x] Shared `database/` package with async SQLAlchemy setup
- [x] SQLAlchemy models:
  - `Listing` (shared) - core listing data
  - `ListingImage` (posting) - images with position ordering
  - `PostingJob` (posting) - platform posting jobs with status tracking
  - `Buyer` (messaging) - buyer profiles
  - `Conversation` (messaging) - conversation threads linked to listings
  - `Message` (messaging) - individual messages with role/delivery tracking
  - `BrowserSession` (messaging) - Stagehand session tracking
  - `ResponseConfig` (messaging) - AI response configuration
- [x] Pydantic schemas for API request/response validation (both services)

### Phase 2: Posting API Endpoints ✅ COMPLETE
- [x] `POST /api/listings` - Create listing with images (multipart form)
- [x] `GET /api/listings` - List all listings with images
- [x] `GET /api/listings/{id}` - Get single listing
- [x] `PUT /api/listings/{id}` - Update listing
- [x] `DELETE /api/listings/{id}` - Delete listing and images
- [x] `POST /api/listings/{id}/post` - Create posting job
- [x] `GET /api/jobs` - List jobs with filtering
- [x] `GET /api/jobs/{id}` - Get job with logs
- [x] `POST /api/jobs/{id}/retry` - Retry failed job
- [x] Image serving via `/uploads/` static mount
- [x] CORS configured for frontend

### Phase 3: Frontend UI ✅ COMPLETE
- [x] Layout with Header navigation
- [x] Dashboard page with listings grid
- [x] Status badges (pending=yellow, posting=blue, posted=green, failed=red)
- [x] Create listing form with drag-drop image upload
- [x] Listing detail page with:
  - Image gallery
  - Description display
  - Platform selector dropdown
  - Post button
  - Posting history with status
  - Retry button for failed jobs
  - Expandable job logs

### Phase 4: Stagehand Automation ✅ COMPLETE
- [x] `PlatformPoster` abstract base class
- [x] `PlatformRegistry` for platform registration
- [x] `FacebookMarketplacePoster` using Stagehand:
  - Browserbase context support for persistent Facebook login cookies
  - CAPTCHA solving enabled
  - Login page detection
  - Navigates to Marketplace create page
  - Uses `execute()` for autonomous form filling
  - Uses `extract()` to get confirmation URL
- [x] Background worker polling every 5 seconds
- [x] Job processor with logging
- [x] `setup_facebook_login.py` helper script for Browserbase auth setup

### Phase 5: Messaging Service ✅ COMPLETE
- [x] **Browser monitoring** - Stagehand-based Messenger polling loop
  - `MessageMonitor` with configurable poll intervals and session breaks
  - Conversation list extraction and message extraction
  - Browser actions (navigate, click conversation, send message)
  - Facebook login via Browserbase context
- [x] **AI auto-responder** - GPT-powered response generation
  - Listing-aware context building (matches conversations to listings)
  - Structured JSON output for responses
  - Configurable system prompts
- [x] **Conversation management**
  - Buyer tracking and matching service
  - Conversation service with full CRUD
  - Automatic listing-to-conversation matching
- [x] **Messaging API endpoints**:
  - `GET /conversations` - List conversations (filterable by status)
  - `GET /conversations/{id}` - Get conversation with messages
  - `GET /conversations/{id}/messages` - Paginated messages
  - `POST /conversations/{id}/messages` - Send manual message
  - `PATCH /conversations/{id}` - Update status/listing match
  - `POST /polling/start` - Start message monitoring
  - `POST /polling/stop` - Stop message monitoring
  - `GET /polling/status` - Get polling state (running, cycle count, errors)
  - `POST /browser/login` - Open headed browser for Facebook login
  - `GET /stats` - Dashboard stats (conversations, messages, buyers)

### Phase 6: Polish ✅ COMPLETE
- [x] Retry functionality (max 3 retries)
- [x] Job logs viewing in UI
- [x] Error handling throughout
- [x] Config loading from shared `.env` file
- [x] Shared database package (refactored out of posting service)

---

## Project Structure

```
bye-buy/
├── backend/
│   ├── database/                      # Shared DB package
│   │   ├── connection.py              # Base, engine, get_session (async)
│   │   ├── schema.sql                 # SQL schema
│   │   └── models/
│   │       └── listing.py             # Listing model (shared)
│   ├── posting/                       # Port 8000
│   │   ├── main.py                    # FastAPI app with lifespan
│   │   ├── config.py                  # Settings from .env
│   │   ├── api/
│   │   │   ├── router.py             # Main API router
│   │   │   ├── listings.py           # Listing CRUD
│   │   │   └── jobs.py               # Job management
│   │   ├── models/
│   │   │   ├── image.py              # ListingImage (backref to Listing)
│   │   │   └── job.py                # PostingJob (backref to Listing)
│   │   ├── schemas/
│   │   │   ├── listing.py            # Pydantic models
│   │   │   └── job.py
│   │   ├── platforms/
│   │   │   ├── base.py               # Abstract PlatformPoster
│   │   │   ├── registry.py           # Platform registry
│   │   │   └── facebook_marketplace.py
│   │   ├── queue/
│   │   │   ├── worker.py             # Background polling
│   │   │   └── job_processor.py      # Job execution
│   │   ├── storage/
│   │   │   └── images.py             # Local file storage
│   │   └── uploads/                   # Image directory
│   ├── messaging/                     # Port 8001
│   │   ├── main.py                    # FastAPI app with lifespan
│   │   ├── config.py                  # Settings from .env
│   │   ├── api/
│   │   │   ├── router.py             # Main API router
│   │   │   ├── conversations.py      # Conversation CRUD
│   │   │   ├── polling.py            # Monitor start/stop/status
│   │   │   └── stats.py              # Dashboard stats
│   │   ├── models/
│   │   │   ├── buyer.py              # Buyer profiles
│   │   │   ├── conversation.py       # Conversation threads
│   │   │   ├── message.py            # Individual messages
│   │   │   ├── browser_session.py    # Session tracking
│   │   │   └── response_config.py    # AI response settings
│   │   ├── schemas/
│   │   │   ├── conversation.py       # Pydantic models
│   │   │   ├── message.py
│   │   │   └── polling.py
│   │   ├── browser/
│   │   │   ├── client.py             # Stagehand session management
│   │   │   ├── auth.py               # Facebook login flow
│   │   │   ├── monitor.py            # MessageMonitor polling loop
│   │   │   ├── extractor.py          # Conversation/message extraction
│   │   │   └── actions.py            # Navigate, click, send message
│   │   ├── ai/
│   │   │   ├── client.py             # OpenAI client wrapper
│   │   │   ├── context.py            # Listing-aware context building
│   │   │   ├── prompts.py            # System prompt generation
│   │   │   └── responder.py          # Response generation
│   │   └── services/
│   │       ├── conversation_service.py
│   │       ├── buyer_service.py
│   │       └── matching_service.py
│   ├── setup_facebook_login.py        # Browserbase FB login helper
│   ├── pyproject.toml
│   └── uv.lock
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx               # Redirect to dashboard
    │   │   ├── layout.tsx             # Root layout with Header
    │   │   ├── dashboard/page.tsx     # Listings grid
    │   │   └── listings/
    │   │       ├── new/page.tsx       # Create form
    │   │       └── [id]/page.tsx      # Detail view
    │   ├── components/
    │   │   ├── ui/
    │   │   │   ├── Button.tsx
    │   │   │   ├── Card.tsx
    │   │   │   ├── Input.tsx
    │   │   │   └── StatusBadge.tsx
    │   │   ├── listings/
    │   │   │   ├── ListingCard.tsx
    │   │   │   ├── ListingGrid.tsx
    │   │   │   ├── ListingForm.tsx
    │   │   │   └── JobLogs.tsx
    │   │   └── layout/
    │   │       └── Header.tsx
    │   └── lib/
    │       ├── api.ts                 # API client
    │       └── types.ts               # TypeScript interfaces
    └── package.json

```

---

## Configuration Required

### Backend `.env` file (`/backend/.env`)
```env
# Browserbase (required for posting + messaging browser automation)
BROWSERBASE_API_KEY=your-browserbase-api-key
BROWSERBASE_PROJECT_ID=your-browserbase-project-id
BROWSERBASE_CONTEXT_ID=               # Set via setup_facebook_login.py

# AI keys
MODEL_API_KEY=your-openai-api-key     # Used by Stagehand
OPENAI_API_KEY=your-openai-api-key    # Used by messaging auto-responder
```

### Facebook Login Setup
```bash
cd backend
# Set env vars first, then run:
BROWSERBASE_API_KEY=... BROWSERBASE_PROJECT_ID=... uv run python setup_facebook_login.py
```
This opens a Browserbase Live View where you log into Facebook. The script saves the context ID for persistent cookies.

---

## Running the Application

### Backend
```bash
cd backend
uv sync                    # Install dependencies

# Posting service
uv run uvicorn posting.main:app --reload --port 8000

# Messaging service (separate terminal)
uv run uvicorn messaging.main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm install               # Install dependencies
npm run dev               # Start dev server on port 3000
```

### Access
- Frontend: http://localhost:3000
- Posting API: http://localhost:8000 (docs: http://localhost:8000/docs)
- Messaging API: http://localhost:8001 (docs: http://localhost:8001/docs)

---

## API Testing

### Posting Service (port 8000)
```bash
# Create listing
curl -X POST http://localhost:8000/api/listings \
  -F "title=iPhone 15" \
  -F "description=Brand new" \
  -F "price=800" \
  -F "images=@photo.jpg"

# List listings
curl http://localhost:8000/api/listings

# Post to Facebook Marketplace
curl -X POST http://localhost:8000/api/listings/1/post \
  -H "Content-Type: application/json" \
  -d '{"platform": "facebook_marketplace"}'

# Check job status
curl http://localhost:8000/api/jobs/1

# Retry failed job
curl -X POST http://localhost:8000/api/jobs/1/retry
```

### Messaging Service (port 8001)
```bash
# Start monitoring Messenger
curl -X POST http://localhost:8001/polling/start

# Check polling status
curl http://localhost:8001/polling/status

# Stop monitoring
curl -X POST http://localhost:8001/polling/stop

# List conversations
curl http://localhost:8001/conversations

# Get conversation with messages
curl http://localhost:8001/conversations/1

# Get dashboard stats
curl http://localhost:8001/stats
```

---

## Known Issues / TODO

1. **Image Upload to Facebook**: Uses Stagehand's `execute()` which may not handle file uploads. May need Browserbase's direct Playwright access for file inputs.
2. **eBay/Craigslist**: Platform registry is ready but implementations not yet created.
3. **Messaging frontend**: No UI for the messaging service yet (API-only).

---

## Future Enhancements

- [ ] Messaging dashboard UI in frontend
- [ ] Add eBay poster implementation
- [ ] Add Craigslist poster implementation
- [ ] Add authentication/user accounts
- [ ] Add scheduling for posts
- [ ] Add bulk posting
- [ ] Add image optimization/compression
- [ ] Add webhook notifications
