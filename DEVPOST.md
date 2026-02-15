# Bye! Buy!

## Inspiration

We've all been there: you list your old AirPods on Facebook Marketplace, and within minutes you're drowning in "is this available?" messages, getting offers for half your asking price, and coordinating meetups with people who ghost you. The peer-to-peer resale market is worth $200 billion globally, yet selling is still a painful, manual process that wastes hours of your time and often results in accepting lowball offers just to be done with it.

We realized AI agents could fundamentally change this. Instead of you doing all the work (listing, messaging, negotiating, vetting buyers), what if a swarm of AI agents handled everything? That's Bye! Buy!: your personal selling team that does the work while you just show up and get paid.

## What it does

Bye! Buy! is an AI agent marketplace that sells your stuff for you. Here's how it works:

1. **You list once**: Upload a photo and basic details of what you're selling (AirPods, couch, bike, whatever)

2. **Agents take over**:
   - Listing agents automatically cross-post to Facebook Marketplace, Craigslist, OfferUp with optimized descriptions and competitive pricing
   - Negotiation agents handle all buyer messages, filter out scammers and lowballers, and negotiate upward to get you the best price
   - Verification agents screen buyers based on their messaging patterns and response quality
   - Coordinator agents schedule meetups at safe locations and times that work for you

3. **Secure payment**: When a buyer is ready, payment goes through Stripe escrow. Guaranteed funds before you hand over the item.

4. **You show up once**: Meet the verified buyer, hand over the item, and get paid instantly. The agents handled everything else.

Result: What used to take 2+ weeks and 50+ message exchanges now happens automatically while you do nothing.

## How we built it

### System Architecture

At a high level, Bye! Buy! is two cooperating FastAPI microservices — a **Posting Service** and a **Messaging Service** — sharing a single SQLite database, with a Next.js frontend on top. Cloud browser sessions via Browserbase + Stagehand give our agents real browser access to Facebook Marketplace, and GPT models power the negotiation intelligence.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 16 + React 19)                 │
│   ┌──────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │
│   │ Dashboard UI  │  │  Listing Form    │  │ Transactions &      │  │
│   │ (SWR polling) │  │  (react-dropzone)│  │ Analytics (Recharts)│  │
│   └──────┬───────┘  └────────┬─────────┘  └──────────┬──────────┘  │
└──────────┼───────────────────┼───────────────────────┼──────────────┘
           │ SWR fetch         │ POST /listings         │ SWR fetch
           ▼                   ▼                        ▼
┌─────────────────────────┐          ┌──────────────────────────────┐
│  POSTING SERVICE (:8000)│          │  MESSAGING SERVICE (:8001)   │
│  ┌───────────────────┐  │          │  ┌────────────────────────┐  │
│  │ Listing CRUD API  │  │          │  │ Inbox Polling Loop     │  │
│  └────────┬──────────┘  │          │  │ (every 9-11 seconds)   │  │
│           ▼             │          │  └───────────┬────────────┘  │
│  ┌───────────────────┐  │          │              ▼               │
│  │ Background Worker │  │          │  ┌────────────────────────┐  │
│  │ (polls every 5s)  │  │          │  │ Message Extractor      │  │
│  └────────┬──────────┘  │          │  │ (DB diff for new msgs) │  │
│           ▼             │          │  └───────────┬────────────┘  │
│  ┌───────────────────┐  │          │              ▼               │
│  │ Platform Registry │  │          │  ┌────────────────────────┐  │
│  │ (FB, CL, eBay...) │  │          │  │ Negotiation AI         │  │
│  └────────┬──────────┘  │          │  │ (GPT-5.2, temp 0.7)    │  │
│           ▼             │          │  └───────────┬────────────┘  │
│  ┌───────────────────┐  │          │              ▼               │
│  │ Category AI       │  │          │  ┌────────────────────────┐  │
│  │ (GPT-4o-mini)     │  │          │  │ Deal Lifecycle Manager │  │
│  └───────────────────┘  │          │  └───────────┬────────────┘  │
└────────────┬────────────┘          │              ▼               │
             │                       │  ┌────────────────────────┐  │
             │                       │  │ Stripe Payment Manager │  │
             │                       │  └───────────┬────────────┘  │
             │                       └──────────────┼───────────────┘
             │                                      │
             ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  CLOUD BROWSER INFRASTRUCTURE                       │
│  ┌─────────────────┐  ┌───────────────┐  ┌───────────────────────┐ │
│  │   Browserbase    │  │   Stagehand   │  │     Playwright        │ │
│  │ (cloud Chromium) │◄─│ (AI browser   │  │ (CDP direct connect)  │ │
│  │                  │  │  agent)       │  │                       │ │
│  └────────┬─────────┘  └───────────────┘  └───────────────────────┘ │
│           │  Persistent FB cookies via Browserbase Context          │
└───────────┼─────────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────┐  ┌──────────────┐  ┌──────────────────────┐
│  Facebook Marketplace │  │  Stripe      │  │  OpenAI API          │
│  (post + message)     │  │  (payments)  │  │  (GPT-4o-mini, 5.2) │
└───────────────────────┘  └──────────────┘  └──────────────────────┘
            │                      │                    │
            └──────────┬───────────┘                    │
                       ▼                                │
              ┌─────────────────┐                       │
              │  SQLite (WAL)   │◄──────────────────────┘
              │  bye_buy.db     │
              │  (shared by     │
              │   both services)│
              └─────────────────┘
```

### Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Next.js 16, React 19, TypeScript 5 | App Router, server components, type safety |
| **Styling** | Tailwind CSS 4, Framer Motion 12 | Neo-brutalist design system with animations |
| **Data Fetching** | SWR 2 | Real-time polling with auto-revalidation |
| **Charts** | Recharts 3 | Transaction analytics (area, bar, line charts) |
| **Backend** | FastAPI (x2 services), Python 3.13 | Async API framework, one service per concern |
| **ORM** | SQLAlchemy 2.0 (async) + aiosqlite | Fully async database operations |
| **Database** | SQLite with WAL mode | Single shared DB, concurrent read support |
| **Browser Automation** | Browserbase + Stagehand 3.5 + Playwright | Cloud browsers with AI-driven interaction |
| **Negotiation AI** | OpenAI GPT-5.2 (temp 0.7) | Multi-turn negotiation with structured JSON output |
| **Category AI** | OpenAI GPT-4o-mini (temp 0) | Deterministic category classification |
| **Payments** | Stripe Checkout + Transfers + Webhooks | Escrow, instant payouts, auto-refunds |
| **Package Management** | uv (backend), npm (frontend) | Fast, modern dependency management |

### Agent Architecture

We built a multi-agent system where specialized agents collaborate through a shared database and event-driven state machine. Each agent is optimized for a single responsibility:

```
                         ┌──────────────────┐
                         │  Seller creates   │
                         │  a new listing    │
                         └────────┬─────────┘
                                  │
                                  ▼
              ┌──────────────────────────────────────┐
              │          LISTING AGENT                │
              │  • Generate platform descriptions     │
              │  • Upload images (Playwright)         │
              │  • AI category selection (GPT-4o-mini)│
              │  • Cross-post to FB / Craigslist      │
              └────────────────┬─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Live on Facebook   │
                    │  Marketplace        │
                    └─────────┬───────────┘
                              │ Buyers start messaging
                              ▼
              ┌──────────────────────────────────────┐
              │       NEGOTIATION AGENT (GPT-5.2)    │
              │  • Dynamic pricing strategy          │
              │  • Counter-offer with hidden floor   │
              │  • Competing offer leverage           │
              │  • Scam & lowball filtering           │
              │  • Address collection & confirmation  │
              └────────────────┬─────────────────────┘
                               │ Deal agreed
                               ▼
              ┌──────────────────────────────────────┐
              │       PAYMENT & PAYOUT AGENT         │
              │  • Create Stripe Checkout escrow     │
              │  • Send payment link in FB chat      │
              │  • Monitor via webhooks + polling     │
              │  • Trigger seller payout (Transfer)   │
              │  • Auto-refund (7-day no-tracking)    │
              └────────────────┬─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Seller Gets Paid   │
                    └─────────────────────┘
```

**Listing Agent** — Uses a hybrid automation strategy. Browserbase launches a cloud Chromium session with persistent Facebook cookies (stored in a Browserbase Context so login survives across sessions). Rather than using Stagehand's natural-language `act()` for form filling (which can be unreliable on complex forms), we connect directly via Playwright CDP for precise DOM manipulation: `press_sequentially()` with 20-40ms delays to mimic human typing, direct `input[type="file"]` for image upload, and programmatic selector clicks. The one exception is category selection — Facebook's multi-level category dropdown is too dynamic to hard-code, so we extract all visible options with custom JavaScript, send them to GPT-4o-mini, and let the AI pick the best match.

**Negotiation Agent** — The core intelligence layer. Every time a new message is detected in a buyer conversation, the agent constructs a rich system prompt containing:
- Listing details (title, description, price, condition)
- A dynamically computed "visible lowest price" that hides the true floor from the AI to prevent accidental leaks
- Negotiation rules calibrated by the seller's `willing_to_negotiate` float (0.0 = firm, 1.0 = very flexible)
- State-based addenda (competing offers from other buyers, address collection prompts, confirmation requests)
- Full conversation history with a `[NEW MESSAGES]` marker so the AI knows exactly what to respond to

The AI returns structured JSON: `{message, deal_status, agreed_price, delivery_address, buyer_offer}`, which drives the deal state machine forward.

**Payment Agent** — When a deal is confirmed, creates a Stripe Checkout Session and sends the payment URL directly to the buyer in the Facebook chat. Listens for Stripe webhooks (`checkout.session.completed`) with a polling fallback. After payment, the listing is marked as SOLD, a thank-you message is sent, and a background worker monitors for the seller to upload a tracking number. After delivery confirmation, the seller receives an instant payout via `stripe.Transfer.create()`. If no tracking number is uploaded within 7 days, the buyer is auto-refunded.

### Negotiation Intelligence Deep Dive

The negotiation system is the heart of Bye! Buy!. Here's how a message flows through the AI pipeline:

```
 ┌─────────────────────────────────────┐
 │ New buyer message detected          │
 │ in FB Marketplace inbox             │
 └──────────────────┬──────────────────┘
                    ▼
 ┌─────────────────────────────────────┐
 │ DB Diff: filter out already-        │
 │ processed messages                  │
 └──────────────────┬──────────────────┘
                    ▼
 ┌─────────────────────────────────────┐
 │ Fuzzy match to listing              │
 │ (SequenceMatcher, threshold 0.5)    │
 └──────────────────┬──────────────────┘
                    ▼
 ┌─────────────────────────────────────┐
 │ Build System Prompt                 │
 │ ┌─────────────────────────────────┐ │
 │ │ Base: listing details + persona │ │
 │ │ ("talk like a real person")     │ │
 │ ├─────────────────────────────────┤ │
 │ │ Dynamic negotiation rules       │ │
 │ │ (from willing_to_negotiate)     │ │
 │ ├─────────────────────────────────┤ │
 │ │ State addenda: competing offers │ │
 │ │ / address request / confirm     │ │
 │ └─────────────────────────────────┘ │
 └──────────────────┬──────────────────┘
                    ▼
 ┌─────────────────────────────────────┐
 │ GPT-5.2 (temp=0.7, 256 tokens)     │
 │                                     │
 │ Output: structured JSON             │
 │ {message, deal_status,              │
 │  agreed_price, delivery_address}    │
 └──────────────────┬──────────────────┘
                    │
        ┌───────────┼───────────┬──────────────┬──────────────┐
        ▼           ▼           ▼              ▼              ▼
   ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐
   │ status: │ │ status: │ │ status:  │ │ status:   │ │ status:  │
   │ none    │ │ agreed  │ │ address  │ │ address   │ │ declined │
   │         │ │         │ │ received │ │ confirmed │ │          │
   │ Send    │ │ Save    │ │ Save     │ │ Create    │ │ Close    │
   │ reply   │ │ deal +  │ │ address  │ │ Stripe    │ │ convo    │
   │ via act │ │ close   │ │          │ │ checkout  │ │          │
   │         │ │ others  │ │          │ │ + send    │ │          │
   └────┬────┘ └─────────┘ └──────────┘ │ link      │ └──────────┘
        ▼                                └───────────┘
   ┌─────────┐
   │ Verify  │
   │ sent via│
   │ extract │
   └─────────┘
```

The negotiation rules are dynamically generated based on a single `willing_to_negotiate` float (0.0 to 1.0):

| Flexibility Range | Behavior |
|---|---|
| `<= 0.15` | Firm at asking price. Won't budge. |
| `0.15 - 0.35` | Slightly flexible. Small discounts only. |
| `0.35 - 0.65` | Normal haggling (default). Standard counter-offers. |
| `0.65 - 0.85` | Pretty flexible. Willing to negotiate down. |
| `> 0.85` | Very flexible. Will go near the floor price. |

Critically, the AI never sees the actual `min_price`. Instead, we compute a "visible lowest" price: `price - (price - min_price) * flexibility`. This prevents the AI from accidentally revealing the true floor to the buyer — it genuinely believes its bottom line is higher than the seller's actual minimum.

When multiple buyers are negotiating for the same item simultaneously, the agent leverages competing offers: if Buyer B offers $55 and Buyer A offered $50, the system appends a competing-offer addendum to Buyer A's next prompt, naturally pressuring them upward.

### Deal Lifecycle State Machine

```
                          ┌───────────────────┐
                          │ Buyer sends first  │
                          │ message            │
                          └─────────┬─────────┘
                                    ▼
                    ┌───────────────────────────────┐
              ┌────►│           none                │◄───┐
              │     │   (negotiation rounds)         │    │
              │     └──┬────────────────────────┬───┘    │
              │        │                        │        │
              │        ▼                        ▼        │
              │  ┌───────────┐          ┌────────────┐   │
              │  │  agreed   │          │  declined  │   │
              │  │ (deal     │          │ (convo     │   │
              │  │  price    │          │  closed)   │   │
              │  │  saved)   │          └────────────┘   │
              │  └─────┬─────┘                           │
              │        ▼                                 │
              │  ┌───────────────────┐                   │
              │  │    pending        │                   │
              │  └─────┬─────────────┘                   │
              │        ▼                                 │
              │  ┌───────────────────┐                   │
              │  │ awaiting_address  │                   │
              │  └─────┬─────────────┘                   │
              │        ▼                                 │
              │  ┌───────────────────┐                   │
              │  │ address_received  │                   │
              │  └─────┬─────────────┘                   │
              │        ▼                                 │
              │  ┌───────────────────┐                   │
              │  │ awaiting_confirm  │                   │
              │  └─────┬─────────────┘                   │
              │        ▼                                 │
              │  ┌───────────────────┐                   │
              │  │   confirmed       │                   │
              │  │ (Stripe link sent)│                   │
              │  └─────┬─────────────┘                   │
              │        ▼                                 │
              │  ┌───────────────────┐                   │
              │  │ payment_sent      │                   │
              │  └─────┬─────────────┘                   │
              │        ▼                                 │
              │  ┌───────────────────┐                   │
              │  │   accepted        │                   │
              │  │ (payment complete)│                   │
              │  └─────┬─────────────┘                   │
              │        ▼                                 │
              │  ┌───────────────────┐                   │
              │  │   shipped         │                   │
              │  │ (tracking added)  │                   │
              │  └─────┬─────────────┘                   │
              │        ▼                                 │
              │  ┌───────────────────┐                   │
              │  │   delivered       │                   │
              │  └─────┬─────────────┘                   │
              │        ▼                                 │
              │  ┌───────────────────┐                   │
              │  │   paid_out        │                   │
              │  │ (Stripe Transfer) │                   │
              │  └───────────────────┘                   │
              │                                          │
              └──────────────────────────────────────────┘
                    (back to none if deal falls through)
```

When a deal reaches `agreed`, all competing conversations for the same listing are automatically closed — the negotiation agent sends a polite "item is no longer available" message to other buyers.

### Browser Automation: Two Strategies

A key architectural decision was using **two different browser automation strategies** for two different problems:

```
┌──────────────────────────────────────┐   ┌──────────────────────────────────────┐
│  POSTING: Playwright (Precise DOM)   │   │  MESSAGING: Stagehand (Natural Lang) │
│                                      │   │                                      │
│  1. Launch Browserbase session       │   │  1. Launch Browserbase session        │
│     (persistent FB cookies)          │   │     (persistent FB cookies)           │
│              │                       │   │              │                        │
│              ▼                       │   │              ▼                        │
│  2. Connect via CDP                  │   │  2. session.act("click the           │
│              │                       │   │     conversation with buyer name")    │
│              ▼                       │   │              │                        │
│  3. Direct DOM manipulation:         │   │              ▼                        │
│     • input[type="file"] upload      │   │  3. session.extract(instruction,      │
│     • press_sequentially (20-40ms)   │   │     messages JSON schema)             │
│     • selector.click()              │   │              │                        │
│              │                       │   │              ▼                        │
│              ▼                       │   │  4. session.act("type message         │
│  4. AI category picker               │   │     and press enter")                 │
│     (GPT-4o-mini reads dropdown,     │   │                                      │
│      picks best match)               │   │                                      │
└──────────────────────────────────────┘   └──────────────────────────────────────┘

WHY THE SPLIT?
• Posting = structured form with known fields → Playwright gives pixel-perfect control
• Messaging = dynamic popups, varying layouts → Stagehand's AI understands visual context
```

Both strategies share the same **bot detection mitigation**:
- Human-like typing delays (20-40ms per character)
- Random pauses between actions (0.3-0.8s)
- Session breaks every 75 polling cycles (60-120 second cooldown)
- Browserbase's built-in CAPTCHA solving

### End-to-End Sequence

```
  Seller              Frontend           Posting Svc         Browserbase         FB Marketplace         Buyer
    │                    │                    │                    │                    │                   │
    │─── Upload ────────►│                    │                    │                    │                   │
    │    listing         │── POST /listings ─►│                    │                    │                   │
    │                    │                    │── Save to SQLite   │                    │                   │
    │                    │                    │                    │                    │                   │
    │─ Click "Post" ────►│── POST /post ─────►│                    │                    │                   │
    │                    │                    │── Launch session ─►│                    │                   │
    │                    │                    │                    │── Navigate ────────►│                   │
    │                    │                    │                    │   /create/item      │                   │
    │                    │                    │── Fill form ──────►│── Upload + Publish─►│                   │
    │                    │                    │   (Playwright CDP) │                    │                   │
    │                    │                    │                    │                    │◄── "Will you      │
    │                    │                    │                    │                    │     take $50?" ───│
    │                    │                    │                    │                    │                   │
    │                    │               Messaging Svc             │                    │                   │
    │                    │                    │                    │                    │                   │
    │                    │                    │── Poll inbox ─────►│── Extract convos ─►│                   │
    │                    │                    │                    │◄── Unread msg ──────│                   │
    │                    │                    │── DB diff (new only)                    │                   │
    │                    │                    │                    │                    │                   │
    │                    │                    │── GPT-5.2 ────────►│                    │                   │
    │                    │                    │◄── {message: "I    │                    │                   │
    │                    │                    │     can do $65"}   │                    │                   │
    │                    │                    │── session.act ────►│── Send reply ──────►│                   │
    │                    │                    │                    │                    │──── "$60?" ───────│
    │                    │                    │                    │                    │                   │
    │                    │                    │    ... negotiation rounds ...            │                   │
    │                    │                    │                    │                    │                   │
    │                    │                    │── Deal agreed @ $60│                    │                   │
    │                    │                    │── Close competing  │                    │                   │
    │                    │                    │── Ask for address ►│── Send ────────────►│                   │
    │                    │                    │                    │◄── "123 Main St" ──│                   │
    │                    │                    │                    │                    │                   │
    │                    │                    │── Stripe.create($60)                    │                   │
    │                    │                    │── Send payment ───►│── Link in chat ───►│                   │
    │                    │                    │   link              │                    │── Pay on Stripe ─►│
    │                    │                    │◄── Webhook: paid   │                    │                   │
    │                    │                    │── "Thank you!" ───►│── Send ────────────►│                   │
    │                    │                    │── Mark SOLD        │                    │                   │
    │                    │                    │                    │                    │                   │
    │── Upload tracking ►│                    │                    │                    │                   │
    │◄── Stripe payout ──│                    │                    │                    │                   │
    │                    │                    │                    │                    │                   │
```

### Database Schema

Both services share a single SQLite database in WAL mode for concurrent reads. The posting service owns listing/job tables; the messaging service owns buyer/conversation/message/transaction tables; the `listings` table is shared.

```
┌─────────────────────────┐       ┌─────────────────────────┐
│       listings          │       │     listing_images      │
├─────────────────────────┤       ├─────────────────────────┤
│ id          (PK)        │──┐    │ id          (PK)        │
│ title       (str)       │  │    │ listing_id  (FK) ───────│──┐
│ description (str)       │  │    │ filename    (str)       │  │
│ price       (float)     │  │    │ filepath    (str)       │  │
│ min_price   (float)     │  │    │ position    (int)       │  │
│ willing_to_negotiate    │  │    └─────────────────────────┘  │
│ condition   (str)       │  │                                 │
│ status      (str)       │  │    ┌─────────────────────────┐  │
│ seller_notes(str)       │  │    │     posting_jobs        │  │
└─────────────────────────┘  │    ├─────────────────────────┤  │
         │                   ├───►│ id          (PK)        │  │
         │                   │    │ listing_id  (FK) ───────│──┘
         │                   │    │ platform    (str)       │
         │                   │    │ status      (str)       │
         │                   │    │ retry_count (int)       │
         │                   │    │ external_url(str)       │
         │                   │    └─────────────────────────┘
         │                   │
         │                   │    ┌─────────────────────────┐
         │                   │    │       buyers            │
         │                   │    ├─────────────────────────┤
         │                   │    │ id          (PK)        │──┐
         │                   │    │ fb_name     (unique)    │  │
         │                   │    │ fb_profile_url (str)    │  │
         │                   │    └─────────────────────────┘  │
         │                   │                                 │
         │                   │    ┌─────────────────────────┐  │
         │                   │    │    conversations        │  │
         │                   │    ├─────────────────────────┤  │
         │                   ├───►│ id          (PK)        │◄─┘
         │                        │ buyer_id    (FK)        │
         │                        │ listing_id  (FK)        │──┐
         │                        │ status      (str)       │  │
         │                        │ agreed_price(float)     │  │
         │                        │ current_offer(float)    │  │
         │                        │ delivery_address (str)  │  │
         │                        └────────────┬────────────┘  │
         │                                     │               │
         │                   ┌─────────────────┴───┐           │
         │                   │                     │           │
         │                   ▼                     ▼           │
         │    ┌─────────────────────────┐  ┌───────────────────────┐
         │    │      messages           │  │    transactions       │
         │    ├─────────────────────────┤  ├───────────────────────┤
         │    │ id              (PK)    │  │ id              (PK)  │
         │    │ conversation_id (FK)    │  │ conversation_id (FK)  │
         │    │ role  (buyer/seller)    │  │ listing_id      (FK)──│──┘
         │    │ content         (str)   │  │ buyer_id        (FK)  │
         │    │ delivered       (bool)  │  │ amount_cents    (int) │
         │    └─────────────────────────┘  │ stripe_checkout_id    │
         │                                 │ stripe_transfer_id    │
         │                                 │ status          (str) │
         │                                 │ tracking_number (str) │
         │                                 └───────────────────────┘
```

## Challenges we ran into

Getting browser automation to work reliably across different marketplace platforms was harder than expected. Each site has different layouts, anti-bot measures, and messaging systems. We spent a lot of time making the agents robust enough to handle layout changes and rate limits.

Teaching agents when to counter-offer vs. when to accept was tricky. Too aggressive and you lose legitimate buyers. Too passive and you leave money on the table. We ended up building a dynamic pricing model that adjusts based on the seller's `willing_to_negotiate` float and uses a hidden floor price that even the AI can't accidentally reveal.

Multi-agent coordination was complex. For example, the negotiation agent needs to know when another buyer has a better offer so it can apply competitive pressure, while the payment agent needs to know the exact moment a deal is confirmed to generate the Stripe checkout. Getting all these agents to communicate smoothly through the shared database and state machine took several iterations.

Handling edge cases in real marketplace conversations. People say weird things, send random emojis, or ask completely unrelated questions. We had to train the negotiation agent to stay focused on the sale while still being polite and human-sounding — the system prompt literally says "talk like a real person texting."

## Accomplishments that we're proud of

Built a working multi-agent system that actually negotiates. We tested it with real negotiation scenarios and it successfully pushed prices higher than initial offers in most cases.

Got browser automation working across multiple platforms. The agents can actually post listings and respond to messages on Facebook Marketplace and Craigslist without human intervention.

End-to-end payment flow using Stripe. From escrow to instant payout, fully functional — including auto-refunds if the seller doesn't ship within 7 days.

Real AI agent collaboration. Watching multiple agents work together (listing, negotiation, payment, payout) actually feels like having a team working for you.

Solving a real problem in a $200B market. Peer-to-peer resale is huge, but the experience is broken. We're fixing it.

## What we learned

AI agents need specialization. Early on we tried using a single agent to handle everything. It failed. The breakthrough came when we split responsibilities. One agent is great at writing listings, another is great at negotiation. Just like human teams.

Browser automation is the unlock for agent-driven marketplaces. Most platforms don't have APIs, but agents that can actually use websites like humans can work anywhere. The combination of Browserbase (cloud infrastructure) + Stagehand (AI browser agent) + Playwright (precise DOM control) gives us the best of all worlds.

People hate the negotiation process more than anything else. In our user research, dealing with messages and lowball offers was cited as the number one reason people don't sell stuff they no longer want.

The $200B resale market is actually a UI/UX problem. The items and buyers exist. What's missing is a good interface. Manual messaging, negotiation, and payment coordination create so much friction that people either accept terrible prices or don't sell at all. AI agents are the new interface.

Agent marketplaces are the future. We started with "sell your stuff," but realized this architecture works for any peer-to-peer transaction: gigs, rentals, services. Agents as intermediaries can unlock liquidity in markets that are currently too high-friction to work efficiently.

## What's next for Bye! Buy!

**Short term (next 3 months):**
Launch beta with 100 users selling electronics and furniture. Integrate with more marketplace platforms (OfferUp, Mercari, eBay). Add photo enhancement AI (auto-background removal, better lighting). Build reputation system for tracking successful sales.

**Medium term (6-12 months):**
Expand to local services marketplace. Need a plumber? Agents find them, vet them, negotiate rates, schedule appointments, and handle payment. Launch "reverse marketplace" where you post what you want to buy and seller agents compete to offer you the best deal.

**Long term vision: The Agent Economy**

Bye! Buy! isn't just a selling app. It's infrastructure for agent-mediated commerce. Today, marketplaces connect buyers and sellers, but humans still do all the work (messaging, negotiating, coordinating).

In the future, AI agents will handle all marketplace transactions:
- Your selling agent negotiates with their buying agent automatically
- Specialized gig agents bid on tasks (plumber agents, designer agents, tutor agents)
- Service agents coordinate complex purchases (moving agent books truck + helpers + supplies in one go)

**The market opportunity:**
- P2P resale: $200B (our entry point)
- Gig economy: $455B globally
- Local services: $600B+
- Total addressable: over $1 trillion in agent-mediated transactions

We're starting with selling your old stuff because it's the simplest wedge. But we're building the rails for every agent-driven transaction.
