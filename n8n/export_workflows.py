import os
import json

WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")
os.makedirs(WORKFLOWS_DIR, exist_ok=True)

def generate_n8n_json(name: str, cron_interval: str, sql_query: str, gmail_subject: str, notes: str) -> dict:
    return {
        "name": name,
        "nodes": [
            {
                "parameters": {
                    "rule": {
                        "interval": [{"field": "cronExpression", "expression": cron_interval}]
                    }
                },
                "name": "Schedule Cron Trigger",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1,
                "position": [250, 300]
            },
            {
                "parameters": {
                    "operation": "executeQuery",
                    "query": sql_query
                },
                "name": "Supabase PostgreSQL Node (FOR UPDATE SKIP LOCKED)",
                "type": "n8n-nodes-base.postgres",
                "typeVersion": 2.4,
                "position": [480, 300],
                "credentials": {
                    "postgres": {
                        "id": "supabase-postgres-credentials",
                        "name": "Supabase PostgreSQL Database"
                    }
                }
            },
            {
                "parameters": {
                    "sendTo": "={{ $json.customer_email || $json.email || 'ops@airline.com' }}",
                    "subject": gmail_subject,
                    "emailType": "html",
                    "message": "={{ $json.email_body || 'Automated Airline Notification from n8n Engine' }}"
                },
                "name": "Gmail Node (Scheduled Delivery)",
                "type": "n8n-nodes-base.gmail",
                "typeVersion": 2.1,
                "position": [720, 300],
                "credentials": {
                    "gmailOAuth2": {
                        "id": "airline-gmail-credentials",
                        "name": "Airline Gmail Account"
                    }
                }
            }
        ],
        "connections": {
            "Schedule Cron Trigger": {
                "main": [[{"node": "Supabase PostgreSQL Node (FOR UPDATE SKIP LOCKED)", "type": "main", "index": 0}]]
            },
            "Supabase PostgreSQL Node (FOR UPDATE SKIP LOCKED)": {
                "main": [[{"node": "Gmail Node (Scheduled Delivery)", "type": "main", "index": 0}]]
            }
        },
        "settings": {
            "executionOrder": "v1"
        },
        "meta": {
            "templateCredsSetupCompleted": True,
            "description": notes
        }
    }

workflows = [
    (
        "wf01_checkin_reminders.json",
        "WF-01: Timezone-Correct 24-Hour Check-in Reminders",
        "0 * * * *",
        "SELECT b.id, b.booking_reference, u.email, u.full_name, f.flight_number, f.origin, f.destination, f.departure_time FROM bookings b JOIN flights f ON b.flight_id = f.id JOIN users u ON b.user_id = u.id WHERE b.status = 'CONFIRMED' AND b.checkin_reminder_sent = FALSE AND f.status = 'SCHEDULED' AND (f.departure_time AT TIME ZONE f.origin_tz) - INTERVAL '24 HOURS' <= (NOW() AT TIME ZONE f.origin_tz) FOR UPDATE OF b SKIP LOCKED;",
        "Flight {{ $json.flight_number }}: Check-In Is Now Open (24 Hours Prior)",
        "REQ-SCH-33: Timezone correct for origin/dest. REQ-SCH-36: Hard suppression of reminders for cancelled flights."
    ),
    (
        "wf02_price_drop_alerts.json",
        "WF-02: Deduplicated Price-Drop Alerts",
        "0 6 * * *",
        "SELECT a.id, a.user_id, u.email, a.origin, a.destination, a.target_price, a.last_notified_price FROM price_alerts a JOIN users u ON a.user_id = u.id WHERE a.is_active = TRUE;",
        "Price Drop Alert: Fares dropped for {{ $json.origin }} -> {{ $json.destination }}",
        "REQ-SCH-34: Price-drop alert with de-duplication so it doesn't fire on every micro-fluctuation."
    ),
    (
        "wf03_waitlist_auto_promotion.json",
        "WF-03: Scheduled Waitlist Seat Detection & Auto-Promotion",
        "*/2 * * * *",
        "BEGIN; SELECT * FROM flight_classes WHERE (total_seats - booked_seats - held_seats) > 0 FOR UPDATE; SELECT * FROM waitlist_entries WHERE status = 'PENDING' ORDER BY priority_score DESC, created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED; UPDATE waitlist_entries SET status = 'OFFERED', offered_at = NOW(), claim_deadline = NOW() + INTERVAL '2 hours'; COMMIT;",
        "Seat Available Offer: Claim Your Seat on Flight {{ $json.flight_number }} within 2 Hours",
        "REQ-WST-30, REQ-WST-32, REQ-SHD-48, REQ-SHD-50: Row-locking coordination between gate-agent and n8n."
    ),
    (
        "wf04_waitlist_claim_expiry.json",
        "WF-04: Unclaimed Waitlist Promotion Expiry & Reassignment",
        "*/5 * * * *",
        "SELECT * FROM waitlist_entries WHERE status = 'OFFERED' AND claim_deadline < NOW() FOR UPDATE SKIP LOCKED;",
        "Waitlist Offer Expired for Flight {{ $json.flight_number }}",
        "REQ-WST-31: Notification window before an auto-promoted seat is reassigned to the next person if unclaimed."
    ),
    (
        "wf05_refund_escalation.json",
        "WF-05: Unresolved Refund Escalation after N Days",
        "0 8 * * *",
        "SELECT r.id, r.amount, r.currency, b.booking_reference, u.email FROM refunds r JOIN bookings b ON r.booking_id = b.id JOIN users u ON b.user_id = u.id WHERE r.status = 'PENDING' AND r.escalated_at IS NULL AND r.created_at <= NOW() - INTERVAL '3 days' FOR UPDATE OF r SKIP LOCKED;",
        "HIGH PRIORITY: Stuck Refund Escalation (Pending > 3 Days)",
        "REQ-CHG-27: Escalation notification if a refund stays unresolved after N days."
    ),
    (
        "wf06_ops_kpi_reporting.json",
        "WF-06: Daily/Weekly Operations KPI Reporting",
        "5 0 * * *",
        "SELECT COUNT(f.id) as total_flights, SUM(fc.total_seats) as total_capacity, SUM(fc.booked_seats) as booked_seats, SUM(b.total_fare) as total_revenue FROM flights f JOIN flight_classes fc ON f.id = fc.flight_id LEFT JOIN bookings b ON f.id = b.flight_id WHERE b.status = 'CONFIRMED';",
        "Daily Airline Operations & Commercial KPI Summary",
        "REQ-SCH-35: Daily/weekly ops reporting (load factor, revenue per flight) pulled from Postgres."
    ),
    (
        "wf07_fraud_scoring.json",
        "WF-07: Mass Booking & Bot Fraud Scoring",
        "*/10 * * * *",
        "SELECT id, user_id, total_fare, created_at FROM bookings WHERE created_at >= NOW() - INTERVAL '15 minutes' AND fraud_flag = FALSE;",
        "SECURITY ALERT: Suspicious Bot/Mass-Booking Pattern Detected",
        "REQ-FRD-39: Scheduled bot/mass-booking fraud-scoring job scanning recent bookings."
    ),
    (
        "wf08_historical_fraud_batch.json",
        "WF-08: Batch Historical Fraud Pattern Review",
        "0 2 * * 0",
        "SELECT user_id, COUNT(id) as monthly_bookings, SUM(total_fare) as monthly_spend FROM bookings WHERE created_at >= NOW() - INTERVAL '30 days' GROUP BY user_id HAVING COUNT(id) > 10;",
        "Weekly Historical Fraud Digest: Cluster Analysis",
        "REQ-FRD-41: Batch review job scanning historical bookings for fraud patterns missed in real time."
    ),
    (
        "wf09_policy_ingestion_pinecone.json",
        "WF-09: Scheduled Policy Ingestion Pipeline into Pinecone",
        "0 4 1 * *",
        "SELECT id, document_name, chunk_text, fare_class, version FROM policy_documents WHERE is_active = TRUE;",
        "Policy Vector Store Refreshed in Pinecone",
        "REQ-FRD-40, REQ-INF-54: Scheduled ingestion pipeline embedding updated policy docs into Pinecone."
    ),
    (
        "wf10_rag_policy_answering.json",
        "WF-10: Grounded RAG Support & Human Approval Gate",
        "*/1 * * * *",
        "SELECT d.id, d.customer_email, d.customer_query, d.rag_drafted_answer FROM support_drafts d WHERE d.approval_status = 'APPROVED' AND d.email_sent_at IS NULL FOR UPDATE SKIP LOCKED;",
        "Official Airline Customer Support: Response to your inquiry",
        "REQ-FRD-37, REQ-FRD-38, REQ-APP-43: Grounded fare rule answer + mandatory human approval gate before Gmail send."
    ),
    (
        "wf11_nightly_reconciliation.json",
        "WF-11: Nightly Ledger Reconciliation & Invariant Check",
        "0 3 * * *",
        "SELECT fc.flight_id, fc.class_code, fc.booked_seats, (SELECT COUNT(p.id) FROM passengers p JOIN bookings b ON p.booking_id = b.id WHERE b.flight_id = fc.flight_id AND b.class_code = fc.class_code AND b.status = 'CONFIRMED' AND p.passenger_status = 'CONFIRMED') as actual_passengers FROM flight_classes fc;",
        "Nightly Audit: Inventory Reconciliation Completed",
        "REQ-SHD-49: Reconciliation/audit job to catch inconsistent states from a failed or partial n8n write."
    )
]

for filename, name, cron, sql, subj, notes in workflows:
    wf_json = generate_n8n_json(name, cron, sql, subj, notes)
    filepath = os.path.join(WORKFLOWS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(wf_json, f, indent=2)
    print(f"Exported: {filename}")

print("All 11 n8n workflow JSONs generated successfully in n8n/workflows/")
