# AeroCore: Flight Management System (FMS)

> Built strictly based on the capstone specification: `flight_management_system_feature_list.pdf`  
> **Core Architecture Stack**: FastAPI + n8n + Supabase PostgreSQL + Pinecone + Grounded RAG + Gmail

---

## System Overview & Architecture Boundaries

This enterprise Flight Management System enforces the strict architectural separation of responsibilities specified in the primary document:

1. **FastAPI (Live Transactional Write Path)**:
   - Sole write path for commercial flight creation, schedule editing, flight cancellations, seat map definition, live search, seat holds, atomic checkout, and passenger cancellations.
   - Strictly enforces relational invariants (e.g. seat class totals summing to declared capacity, non-negative seat counts, duplicate flight detection, overbooking limits, and price quote expiry).
   - Handles `Idempotency-Key` headers across mutating routes to protect against retried requests.
   - Dispatches synchronous transactional Gmail messages (Booking Confirmation, Cancellation Receipt) post-commit.

2. **n8n (Independent Automation Engine)**:
   - Operates as a completely independent background automation engine that directly accesses Supabase PostgreSQL without code dependencies or calls to FastAPI endpoints.
   - Employs pessimistic row-locking (`SELECT ... FOR UPDATE SKIP LOCKED`) in all polling workflows to prevent double-processing.
   - Executes background automations: 24h timezone-aware check-in reminders, cancelled-flight reminder suppression, deduplicated price-drop alerts, waitlist auto-promotions, unclaimed promotion expirations, stuck refund escalations, daily/weekly operations KPI reporting, and bot fraud scoring.
   - Manages the Pinecone vector index maintenance and orchestrates Grounded RAG policy support with a mandatory human supervisor approval gate prior to Gmail dispatch.

3. **Supabase PostgreSQL (Single Ledger of Truth)**:
   - Stores all flights, seat classes, physical seat maps, bookings, passengers, payments, waitlists, refunds, travel vouchers, and immutable audit logs (`admin_audit_logs`, `system_audit_trail`).
   - Enforces database-level CHECK constraints, unique partial indexes, and custom ENUMs so that direct writes from n8n cannot corrupt inventory.

---

## Directory Structure

```text
flight-management-system/
├── backend/                        # FastAPI Transactional Backend
│   ├── app/
│   │   ├── api/                    # REST API Endpoints (admin, flights, bookings, waitlist, support)
│   │   ├── core/                   # Config, Database Engine, Security, Dependencies, Audit
│   │   ├── models/                 # Declarative SQLAlchemy 2.0 Models
│   │   ├── schemas/                # Strict Pydantic v2 Request/Response Schemas
│   │   ├── services/               # Transactional Gmail Service, Inventory Manager
│   │   └── main.py                 # FastAPI Application Entrypoint & Lifespan Hooks
│   ├── requirements.txt            # Python Dependencies
│   └── .env.example                # Environment Variable Template
├── database/                       # PostgreSQL Database Assets
│   ├── schema.sql                  # Complete Supabase PostgreSQL DDL (21 Tables, Enums, Constraints)
│   ├── seed.sql                    # Initial Data (UK -> Dubai BA105, 20F/30B/50E, 100 Seats, Users)
│   └── init_db.py                  # Database Initializer & Migration Script
├── frontend/                       # Modern Responsive Web Application
│   ├── css/style.css               # Glassmorphic Dark-Mode UI Design System
│   ├── js/app.js                   # Client-Side Logic & API Integrations
│   └── index.html                  # Multi-Portal Web Interface
├── n8n/                            # Independent Automation Engine
│   ├── runner/
│   │   └── standalone_worker.py    # Autonomous Direct-to-Database Background Worker
│   ├── workflows/                  # 11 Importable n8n Workflow JSON Definitions (WF-01 to WF-11)
│   └── export_workflows.py         # Workflow Template Generator
├── rag/                            # Retrieval-Augmented Generation & Pinecone
│   ├── documents/
│   │   └── airline_policies.md     # Official Airline Conditions of Carriage & Fare Rules
│   ├── chunks.json                 # Semantic Chunks with Fare Class Metadata
│   └── ingest.py                   # Chunking & Pinecone Ingestion Script
├── tests/                          # Comprehensive Automated Test Suites
│   ├── test_unit_and_invariants.py # Capacity Sum, Non-Negative, and Constraint Tests
│   ├── test_booking_concurrency_and_idempotency.py # Search, Idempotency, and Group Tests
│   ├── test_cancellations_and_remediation.py # Fare Branching, Partial Repricing, Involuntary Overrides
│   ├── test_concurrency_race.py    # Heavy Concurrent Race Conditions & Overselling Prevention
│   └── test_n8n_and_rag.py         # Waitlist Priority, Grounded RAG, and Approval Gates
├── Dockerfile                      # Production Multi-Stage Docker Build
├── render.yaml                     # Free-Tier Render 1-Click Deployment Blueprint
└── pytest.ini                      # Pytest Configuration
```

---

## 11 Autonomous n8n Workflows Implemented

Each workflow is provided as a standalone direct-to-database worker in `n8n/runner/standalone_worker.py` and as an importable JSON file in `n8n/workflows/`:

1. **WF-01: Timezone-Aware Check-in Reminder** (`wf01_checkin_reminders.json`): Hourly cron identifying flights departing in $\le 24\text{ hours}$ origin local time. Dispatches personalized check-in emails with PNR and seat information.
2. **WF-02: Deduplicated Price-Drop Alert** (`wf02_price_drop_alerts.json`): Daily cron comparing lowest route fares against target prices. Only alerts users if price drops $\ge \$20$ and $\ge 24\text{ hours}$ have elapsed since the previous alert.
3. **WF-03: Waitlist Seat Detection & Auto-Promotion** (`wf03_waitlist_auto_promotion.json`): Polls every 2 minutes for freed seats. Locks `flight_classes` row with `SELECT FOR UPDATE`, selects candidate with highest `priority_score` (Platinum > Gold > Silver > Bronze > None), offers the seat, and starts a 2-hour claim window.
4. **WF-04: Unclaimed Waitlist Promotion Expiry** (`wf04_waitlist_claim_expiry.json`): Polls every 5 minutes for expired offers. Marks status `EXPIRED`, releases seat hold, and immediately offers the seat to candidate #2 in line.
5. **WF-05: Unresolved Refund Escalation** (`wf05_refund_escalation.json`): Daily cron identifying pending refunds older than 3 days. Marks `ESCALATED` and alerts the finance team via Gmail.
6. **WF-06: Operations KPI Reporting** (`wf06_ops_kpi_reporting.json`): Computes daily load factor ($\%$) and confirmed revenue per flight directly from PostgreSQL. Dispatches HTML executive summary to management.
7. **WF-07: Mass-Booking & Bot Fraud Scoring** (`wf07_fraud_scoring.json`): Scans reservations created in the last 15 minutes. Flags high velocity ($>3$ bookings in 30 min) with `fraud_score >= 70` and quarantines tickets.
8. **WF-08: Batch Historical Fraud Review** (`wf08_historical_fraud_batch.json`): Weekly scan analyzing multi-account voucher recycling rings across 30-day historical data.
9. **WF-09: Scheduled Policy Ingestion into Pinecone** (`wf09_policy_ingestion_pinecone.json`): Chunks and embeds updated policy documents into Pinecone namespace `flight-policies`.
10. **WF-10: Grounded RAG Support & Human Approval Gate** (`wf10_rag_policy_answering.json`): Retrieves customer's exact booking and fare type (Basic Economy vs Flexible), drafts an answer grounded in their actual ticket rules, and holds the draft in the supervisor approval queue until signed off.
11. **WF-11: Nightly Ledger Reconciliation** (`wf11_nightly_reconciliation.json`): Nightly audit verifying that `booked_seats` counters match actual active passenger records. Auto-repairs discrepancies and writes to `system_reconciliation_logs`.

---

## Setup & Local Execution Guide

### 1. Initialize Python Environment & Seed Database
```bash
# Seed database (creates all 21 tables and UK->Dubai BA105 flight)
python -m database.init_db
```

### 2. Start FastAPI REST Backend
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- API Root: `http://localhost:8000`
- Interactive OpenAPI / Swagger UI: `http://localhost:8000/docs`

### 3. Open Web Frontend
Simply open `frontend/index.html` in any modern web browser or serve via:
```bash
npx serve frontend -p 3000
```

### 4. Run Independent n8n Background Worker
To simulate the scheduled background automations directly against the database:
```bash
python -m n8n.runner.standalone_worker
```

### 5. Run Complete Automated Test Suite
```bash
python -m pytest -v tests/
```
Output:
```text
tests/test_booking_concurrency_and_idempotency.py PASSED [25%]
tests/test_cancellations_and_remediation.py PASSED       [43%]
tests/test_concurrency_race.py PASSED                    [50%]
tests/test_n8n_and_rag.py PASSED                         [68%]
tests/test_unit_and_invariants.py PASSED                 [100%]
============================= 16 passed in 6.45s ==============================
```

---

## Free-Tier & Live Deployment

| Component | Free-Tier Provider | Setup Instructions |
|---|---|---|
| **Database** | **Supabase PostgreSQL** | Create a free project at [supabase.com](https://supabase.com). In SQL Editor, run `database/schema.sql` followed by `database/seed.sql`. Copy your connection URI to `DATABASE_URL`. |
| **Backend API** | **Render / Fly.io** | Connect GitHub repo to [render.com](https://render.com). Deploy using `render.yaml` or Dockerfile on the free web service plan. |
| **Automation** | **n8n Self-Hosted** | Deploy `n8nio/n8n:latest` on Fly.io / HuggingFace Spaces or run local container connected to Supabase PostgreSQL. Import JSONs from `n8n/workflows/`. |
| **Vector DB** | **Pinecone** | Create a free Serverless index at [pinecone.io](https://pinecone.io) (`flight-policies`, dimension 1536). Run `python -m rag.ingest`. |
| **Email** | **Gmail SMTP** | Generate a Google App Password in your Google Account Security settings. Add `GMAIL_SENDER_EMAIL` and `GMAIL_APP_PASSWORD` to environment variables. |
| **Frontend** | **Vercel / Cloudflare Pages** | Deploy `frontend/` folder directly to Cloudflare Pages or GitHub Pages with zero build step. |

---

## Pre-Seeded Default Accounts

| Role | Email | Password | Loyalty Tier |
|---|---|---|---|
| **Super Admin** | `superadmin@airline.com` | `Admin123!` | PLATINUM |
| **Ops Agent** | `ops.agent@airline.com` | `Agent123!` | GOLD |
| **Passenger 1** | `john.doe@example.com` | `Pass123!` | PLATINUM |
| **Passenger 2** | `jane.smith@example.com` | `Pass123!` | NONE |

---
*Built for the Hackathon Capstone. Conforms strictly to `flight_management_system_feature_list.pdf`.*
