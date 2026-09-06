import os

admin_html_path = r"c:\Users\Hashir Shahid\Desktop\Hackathon\flight-management-system\frontend\admin.html"

with open(admin_html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update rag-gate-tab to match Section 19 perfectly
rag_gate_old = """    <section id="rag-gate-tab" class="tab-content">
      <div class="hero-banner">
        <h1 class="hero-title">AI Grounded Policy Support: Human Supervisor Approval Gate</h1>
        <p class="hero-subtitle">MANDATORY HUMAN SIGN-OFF (REQ-FRD-38, REQ-APP-43): AI-drafted policy responses are held in this queue and CANNOT be dispatched via Gmail until approved by an Operations Supervisor.</p>
      </div>

      <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 1rem;">
          <h2 class="card-title" style="margin-bottom:0;">dY>,? Pending Drafts Queue</h2>
          <button class="btn btn-secondary" onclick="loadSupportDrafts()">Refresh Review Queue</button>
        </div>
        <div id="support-drafts-container">
          <p style="color: var(--text-dim);">Loading pending drafts...</p>
        </div>
      </div>
    </section>"""

# If encoding had replaced emoji, let's find the section via regex or index
import re

rag_section_pattern = re.compile(r'<section id="rag-gate-tab" class="tab-content">.*?</section>', re.DOTALL)

rag_gate_new = """    <section id="rag-gate-tab" class="tab-content">
      <div class="hero-banner">
        <div style="display:inline-block; padding: 0.25rem 0.75rem; background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 9999px; font-size: 0.8rem; font-weight: 800; color: #fbbf24; margin-bottom: 0.5rem;">
          19. 🤖 AI / RAG SUPERVISOR GATEWAY
        </div>
        <h1 class="hero-title">AI Support Human Approval Gate</h1>
        <p class="hero-subtitle">
          Mandatory Human-in-the-Loop Sign-off: AI answers are NEVER emailed directly to passengers without Supervisor review.
          Approve, Edit, or Reject grounded drafts before Gmail dispatch.
        </p>
      </div>

      <!-- Pending Drafts Queue -->
      <div class="card" style="margin-bottom: 1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
          <div>
            <h2 class="card-title" style="margin-bottom:0.2rem; display: flex; align-items: center; gap: 0.5rem;">
              <span>🤖</span> AI Support Approvals Queue
            </h2>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin: 0;">
              AI answers held pending explicit human supervisor approval.
            </p>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="loadSupportDrafts()">🔄 Refresh Review Queue</button>
        </div>

        <div id="support-drafts-container" style="display: flex; flex-direction: column; gap: 1.25rem;">
          <!-- Dynamically populated from /api/v1/admin/rag/approvals -->
        </div>
      </div>
    </section>"""

content = rag_section_pattern.sub(rag_gate_new, content, count=1)

# 2. Update audit-tab to match Section 25 perfectly
audit_section_pattern = re.compile(r'<section id="audit-tab" class="tab-content">.*?</section>', re.DOTALL)

audit_tab_new = """    <section id="audit-tab" class="tab-content">
      <div class="hero-banner">
        <div style="display:inline-block; padding: 0.25rem 0.75rem; background: rgba(96, 165, 250, 0.2); border: 1px solid rgba(96, 165, 250, 0.4); border-radius: 9999px; font-size: 0.8rem; font-weight: 800; color: #93c5fd; margin-bottom: 0.5rem;">
          25. 📝 AUDIT LOGS (IMMUTABLE)
        </div>
        <h1 class="hero-title">Administrative Audit Trail</h1>
        <p class="hero-subtitle">
          Append-only, immutable regulatory ledger. Records Who, What, When, Entity, Old Value, New Value, and Reason for every admin mutation.
        </p>
      </div>

      <!-- Compliance Info Banner -->
      <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: 8px; padding: 0.85rem 1.25rem; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <span style="font-size: 1.5rem;">🛡️</span>
          <div>
            <div style="font-size: 0.9rem; font-weight: 800; color: #93c5fd;">Append-Only Regulatory Ledger • Zero Edit / Delete Policy</div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">Mutations and audit entries are atomically committed within the same database transaction.</div>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="loadAuditLogs()">🔄 Refresh Audit Trail</button>
      </div>

      <!-- Audit Logs Table Card -->
      <div class="card" style="padding: 0; overflow: hidden;">
        <div style="overflow-x: auto;">
          <table class="table" style="margin: 0;">
            <thead>
              <tr>
                <th style="width: 100px;">Time</th>
                <th style="width: 110px;">Admin</th>
                <th>Action</th>
                <th>Entity</th>
                <th>Before</th>
                <th>After</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody id="audit-logs-tbody">
              <!-- Dynamically populated from loadAuditLogs() -->
            </tbody>
          </table>
        </div>
      </div>
    </section>"""

content = audit_section_pattern.sub(audit_tab_new, content, count=1)

# 3. Define new tab sections for Sections 20, 21, 22, 23, 24, 26, 27 + Passengers & SeatMap
new_tabs_html = """
    <!-- =================================================================== -->
    <!-- PASSENGERS REGISTRY TAB (Under MAIN) -->
    <!-- =================================================================== -->
    <section id="passengers-tab" class="tab-content">
      <div class="hero-banner">
        <h1 class="hero-title">Fleet Passengers &amp; Customer Directory</h1>
        <p class="hero-subtitle">Unified registry of passengers, booking histories, issued travel credits, and loyalty profiles.</p>
      </div>

      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem;">
          <div style="display: flex; gap: 0.5rem; flex: 1; max-width: 400px;">
            <input type="text" id="pax-search-input" class="form-input" placeholder="Search passenger by name, email, or PNR..." oninput="filterPassengersTable()">
          </div>
          <button class="btn btn-secondary btn-sm" onclick="loadPassengersRegistry()">🔄 Refresh Passengers</button>
        </div>

        <div style="overflow-x: auto;">
          <table class="table">
            <thead>
              <tr>
                <th>Passenger</th>
                <th>Email</th>
                <th>Bookings</th>
                <th>Active PNRs</th>
                <th>Travel Credits</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="passengers-tbody">
              <!-- Dynamically loaded -->
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- 5. 🪑 SEAT MAP DESIGNER TAB (Under OPERATIONS) -->
    <!-- =================================================================== -->
    <section id="seatmap-tab" class="tab-content">
      <div class="hero-banner">
        <div style="display:inline-block; padding: 0.25rem 0.75rem; background: rgba(167, 139, 250, 0.2); border: 1px solid rgba(167, 139, 250, 0.4); border-radius: 9999px; font-size: 0.8rem; font-weight: 800; color: #c4b5fd; margin-bottom: 0.5rem;">
          5. 🪑 PHYSICAL SEAT MAP DESIGNER
        </div>
        <h1 class="hero-title">Aircraft Seating Layout &amp; Configuration</h1>
        <p class="hero-subtitle">
          Define physical aircraft layout (First, Business, Economy). Active seat count must exactly equal the class capacity specification.
        </p>
      </div>

      <div class="card" style="margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.25rem;">
          <div>
            <label style="font-size: 0.85rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 0.35rem;">Select Flight to Configure:</label>
            <select id="seatmap-flight-selector" class="form-select" style="min-width: 260px;" onchange="onSeatMapFlightChanged()">
              <!-- Dynamically populated with active flights -->
            </select>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-secondary btn-sm" onclick="generateStandardLayoutTab(true)">↺ Reset Standard 100-Seat Layout</button>
            <button class="btn btn-primary btn-sm" onclick="saveSeatMapFromTab()">💾 Save Physical Seat Map</button>
          </div>
        </div>

        <!-- Cabin Allocation Balance equation -->
        <div id="seatmap-tab-validation-banner" class="capacity-live-box match" style="margin-bottom: 1.25rem;">
          <span>Physical Seats: 100 / 100 Class Capacities (First: 20/20, Business: 30/30, Economy: 50/50) ✓</span>
        </div>

        <!-- Physical Grid Display Container -->
        <div id="seatmap-tab-grid-container" style="display: flex; flex-direction: column; gap: 1.5rem;">
          <!-- Rendered by renderSeatMapDesignerGrid() -->
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- 20. 📄 POLICY DOCUMENTS MANAGEMENT (Pinecone RAG Vector Store) -->
    <!-- =================================================================== -->
    <section id="policies-tab" class="tab-content">
      <div class="hero-banner">
        <div style="display:inline-block; padding: 0.25rem 0.75rem; background: rgba(52, 211, 153, 0.2); border: 1px solid rgba(52, 211, 153, 0.4); border-radius: 9999px; font-size: 0.8rem; font-weight: 800; color: #6ee7b7; margin-bottom: 0.5rem;">
          20. 📄 POLICY DOCUMENTS &amp; PINECONE INGESTION
        </div>
        <h1 class="hero-title">Policy Document Management</h1>
        <p class="hero-subtitle">
          Manage regulatory fare policies powering automated RAG responses. Documents are automatically chunked, embedded, and indexed into Pinecone vector storage.
        </p>
      </div>

      <!-- Action & Ingestion Telemetry -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
        <div class="card" style="padding: 1rem; background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08);">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Vector Database</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: #34d399; margin: 0.2rem 0;">Pinecone Serverless</div>
          <div style="font-size: 0.75rem; color: #94a3b8;">Index: airline-policies-v1 • 1536 dim</div>
        </div>
        <div class="card" style="padding: 1rem; background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08);">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Active Policies</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: #60a5fa; margin: 0.2rem 0;" id="policy-count-display">4 Active</div>
          <div style="font-size: 0.75rem; color: #94a3b8;">Covering Basic, Standard, Flex &amp; Business</div>
        </div>
        <div class="card" style="padding: 1rem; background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08);">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Ingestion Pipeline</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: #fbbf24; margin: 0.2rem 0;">n8n OCR + Embeddings</div>
          <div style="font-size: 0.75rem; color: #94a3b8;">Auto-sync on document version change</div>
        </div>
      </div>

      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem;">
          <h2 class="card-title" style="margin-bottom:0;">Indexed Policy Documents</h2>
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-secondary btn-sm" onclick="loadPolicyDocuments()">🔄 Refresh</button>
            <button class="btn btn-primary btn-sm" onclick="openPolicyUploadModal()">➕ Upload New Document</button>
          </div>
        </div>

        <div style="overflow-x: auto;">
          <table class="table">
            <thead>
              <tr>
                <th>Document Title</th>
                <th>Fare Type</th>
                <th>Effective Date</th>
                <th>Version</th>
                <th>Status</th>
                <th>Vector Store</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="policies-table-body">
              <!-- Dynamically populated from /api/v1/admin/policies -->
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- 21. 👨‍⚖️ CENTRAL APPROVAL CENTER -->
    <!-- =================================================================== -->
    <section id="approvals-tab" class="tab-content">
      <div class="hero-banner">
        <div style="display:inline-block; padding: 0.25rem 0.75rem; background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 9999px; font-size: 0.8rem; font-weight: 800; color: #f87171; margin-bottom: 0.5rem;">
          21. 👨‍⚖️ CENTRAL APPROVAL CENTER
        </div>
        <h1 class="hero-title">Operations &amp; Governance Approval Center</h1>
        <p class="hero-subtitle">
          Human sign-off required for Schedule-change compensation, Denied boarding compensation, Special refunds, and AI customer answers.
        </p>
      </div>

      <!-- Pending Categories KPI Cards -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
        <div class="card" style="padding: 1rem; border-left: 4px solid #60a5fa;">
          <div style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted);">Schedule Compensation</div>
          <div style="font-size: 1.8rem; font-weight: 900; color: #60a5fa;" id="appr-stat-sched">4</div>
          <div style="font-size: 0.75rem; color: #94a3b8;">Pending supervisor review</div>
        </div>
        <div class="card" style="padding: 1rem; border-left: 4px solid #f87171;">
          <div style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted);">Denied Boarding</div>
          <div style="font-size: 1.8rem; font-weight: 900; color: #f87171;" id="appr-stat-denied">2</div>
          <div style="font-size: 0.75rem; color: #94a3b8;">High priority statutory SLA</div>
        </div>
        <div class="card" style="padding: 1rem; border-left: 4px solid #fbbf24;">
          <div style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted);">AI Customer Answers</div>
          <div style="font-size: 1.8rem; font-weight: 900; color: #fbbf24;" id="appr-stat-ai">7</div>
          <div style="font-size: 0.75rem; color: #94a3b8;">RAG policy draft validation</div>
        </div>
        <div class="card" style="padding: 1rem; border-left: 4px solid #a78bfa;">
          <div style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted);">Special Refunds</div>
          <div style="font-size: 1.8rem; font-weight: 900; color: #a78bfa;" id="appr-stat-special">3</div>
          <div style="font-size: 0.75rem; color: #94a3b8;">Out-of-policy exceptions</div>
        </div>
      </div>

      <!-- Approvals Tab View Controls -->
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem;">
          <div style="display: flex; gap: 0.5rem;" id="approvals-filter-pills">
            <button class="btn btn-sm btn-primary" onclick="setApprovalsFilter('PENDING', this)">Pending (<span id="count-pending-badge">16</span>)</button>
            <button class="btn btn-sm btn-secondary" onclick="setApprovalsFilter('APPROVED', this)">Approved</button>
            <button class="btn btn-sm btn-secondary" onclick="setApprovalsFilter('REJECTED', this)">Rejected</button>
            <button class="btn btn-sm btn-secondary" onclick="setApprovalsFilter('EXPIRED', this)">Expired</button>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="loadApprovalsCenter()">🔄 Refresh Requests</button>
        </div>

        <div style="overflow-x: auto;">
          <table class="table">
            <thead>
              <tr>
                <th>Request ID</th>
                <th>Passenger</th>
                <th>Booking</th>
                <th>Reason</th>
                <th>Proposed Action</th>
                <th>Amount</th>
                <th>Created</th>
                <th>Requested By</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="approvals-table-body">
              <!-- Dynamically populated from /api/v1/admin/approvals -->
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- 22. 📧 COMMUNICATION & NOTIFICATION LOGS (n8n & Gmail Engine) -->
    <!-- =================================================================== -->
    <section id="notifications-tab" class="tab-content">
      <div class="hero-banner">
        <div style="display:inline-block; padding: 0.25rem 0.75rem; background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 9999px; font-size: 0.8rem; font-weight: 800; color: #93c5fd; margin-bottom: 0.5rem;">
          22. 📧 COMMUNICATION &amp; NOTIFICATION LOGS
        </div>
        <h1 class="hero-title">Dispatch &amp; Email Delivery Telemetry</h1>
        <p class="hero-subtitle">
          Audited log of scheduled n8n Gmail notifications. Automated exponential retries on bounce or rate-limiting with status transition to SENT.
        </p>
      </div>

      <!-- Channel Metrics -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
        <div class="card" style="padding: 1rem; text-align: center;">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">DISPATCHED (24H)</div>
          <div style="font-size: 1.7rem; font-weight: 900; color: #34d399;" id="notif-stat-sent">1,248</div>
          <div style="font-size: 0.75rem; color: #34d399;">SENT ✓</div>
        </div>
        <div class="card" style="padding: 1rem; text-align: center;">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">QUEUED DISPATCH</div>
          <div style="font-size: 1.7rem; font-weight: 900; color: #60a5fa;" id="notif-stat-pending">14</div>
          <div style="font-size: 0.75rem; color: #60a5fa;">PENDING ⏳</div>
        </div>
        <div class="card" style="padding: 1rem; text-align: center;">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">ACTIVE RETRIES</div>
          <div style="font-size: 1.7rem; font-weight: 900; color: #fbbf24;" id="notif-stat-retrying">2</div>
          <div style="font-size: 0.75rem; color: #fbbf24;">RETRYING 🔄</div>
        </div>
        <div class="card" style="padding: 1rem; text-align: center;">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">DELIVERY FAILURES</div>
          <div style="font-size: 1.7rem; font-weight: 900; color: #f87171;" id="notif-stat-failed">1</div>
          <div style="font-size: 0.75rem; color: #f87171;">FAILED ✕</div>
        </div>
      </div>

      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem;">
          <div>
            <h2 class="card-title" style="margin-bottom:0.2rem;">Communication Logs</h2>
            <div style="font-size: 0.8rem; color: var(--text-muted);">Scheduled Gmail workflows dispatch telemetry</div>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <select id="notif-type-filter" class="form-select form-select-sm" onchange="filterNotificationLogs()">
              <option value="ALL">All Types</option>
              <option value="Booking Confirmation">Booking Confirmation</option>
              <option value="Cancellation Receipt">Cancellation Receipt</option>
              <option value="Check-in Reminder">Check-in Reminder</option>
              <option value="AI Reply">AI Reply</option>
            </select>
            <button class="btn btn-secondary btn-sm" onclick="loadCommunicationLogs()">🔄 Refresh Logs</button>
          </div>
        </div>

        <div style="overflow-x: auto;">
          <table class="table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Passenger</th>
                <th>Booking</th>
                <th>Status</th>
                <th>Sent At</th>
                <th>Channel / Engine</th>
                <th>Retries</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="notifications-table-body">
              <!-- Dynamically populated from /api/v1/admin/notifications/logs -->
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- 23. 📊 REPORTS & ANALYTICS -->
    <!-- =================================================================== -->
    <section id="reports-tab" class="tab-content">
      <div class="hero-banner">
        <div style="display:inline-block; padding: 0.25rem 0.75rem; background: rgba(139, 92, 246, 0.2); border: 1px solid rgba(139, 92, 246, 0.4); border-radius: 9999px; font-size: 0.8rem; font-weight: 800; color: #c4b5fd; margin-bottom: 0.5rem;">
          23. 📊 REPORTS &amp; ANALYTICS
        </div>
        <h1 class="hero-title">Executive Operations &amp; Commercial Reports</h1>
        <p class="hero-subtitle">
          Daily and weekly flight operations, load factors, revenue generation, cancellation trends, and fare class performance.
        </p>
      </div>

      <!-- Daily / Weekly Toggle & Export -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem;">
        <div style="display: flex; gap: 0.5rem;">
          <button class="btn btn-primary btn-sm" id="btn-rep-daily" onclick="switchReportsPeriod('daily')">Daily Reports</button>
          <button class="btn btn-secondary btn-sm" id="btn-rep-weekly" onclick="switchReportsPeriod('weekly')">Weekly Summary</button>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="loadReportsAnalytics()">🔄 Refresh Analytics</button>
      </div>

      <!-- KPI Summary Cards (Section 23 Specs) -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem;">
        <div class="card" style="padding: 0.85rem; text-align: center;">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Flights</div>
          <div style="font-size: 1.4rem; font-weight: 800; color: #fff;" id="rep-kpi-flights">18</div>
        </div>
        <div class="card" style="padding: 0.85rem; text-align: center;">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Bookings</div>
          <div style="font-size: 1.4rem; font-weight: 800; color: #60a5fa;" id="rep-kpi-bookings">142</div>
        </div>
        <div class="card" style="padding: 0.85rem; text-align: center;">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Revenue</div>
          <div style="font-size: 1.4rem; font-weight: 800; color: #34d399;" id="rep-kpi-revenue">$78,450</div>
        </div>
        <div class="card" style="padding: 0.85rem; text-align: center;">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Load Factor</div>
          <div style="font-size: 1.4rem; font-weight: 800; color: #fbbf24;" id="rep-kpi-loadfactor">82.4%</div>
        </div>
        <div class="card" style="padding: 0.85rem; text-align: center;">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Cancellation Rate</div>
          <div style="font-size: 1.4rem; font-weight: 800; color: #f87171;" id="rep-kpi-cancels">3.2%</div>
        </div>
        <div class="card" style="padding: 0.85rem; text-align: center;">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Refunds</div>
          <div style="font-size: 1.4rem; font-weight: 800; color: #e879f9;" id="rep-kpi-refunds">$3,200</div>
        </div>
        <div class="card" style="padding: 0.85rem; text-align: center;">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Waitlist</div>
          <div style="font-size: 1.4rem; font-weight: 800; color: #38bdf8;" id="rep-kpi-waitlist">14 Active</div>
        </div>
        <div class="card" style="padding: 0.85rem; text-align: center;">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Fraud Blocked</div>
          <div style="font-size: 1.4rem; font-weight: 800; color: #f43f5e;" id="rep-kpi-fraud">2 Alerts</div>
        </div>
      </div>

      <!-- Graphs Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem;">
        <!-- Graph 1: Revenue Trend -->
        <div class="card">
          <h3 style="font-size: 1.05rem; font-weight: 800; color: #fff; margin-bottom: 0.75rem;">
            📈 Revenue Performance Curve
          </h3>
          <div id="revenue-graph-container" style="background: rgba(15, 23, 42, 0.6); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);">
            <!-- SVG Interactive Curve -->
          </div>
        </div>

        <!-- Graph 2: Load Factor by Flight -->
        <div class="card">
          <h3 style="font-size: 1.05rem; font-weight: 800; color: #fff; margin-bottom: 0.75rem;">
            ✈️ Load Factor by Flight
          </h3>
          <div id="loadfactor-graph-container" style="display: flex; flex-direction: column; gap: 0.75rem;">
            <!-- Rendered load factor bars -->
          </div>
        </div>
      </div>

      <!-- Graph 3 & 4 Grid: Cancellation Trend & Fare-Class Performance -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 1.5rem;">
        <div class="card">
          <h3 style="font-size: 1.05rem; font-weight: 800; color: #fff; margin-bottom: 0.75rem;">
            📉 Cancellation Trend Analysis
          </h3>
          <div id="cancels-graph-container" style="background: rgba(15, 23, 42, 0.6); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);">
            <!-- SVG Curve -->
          </div>
        </div>

        <div class="card">
          <h3 style="font-size: 1.05rem; font-weight: 800; color: #fff; margin-bottom: 0.75rem;">
            🎟️ Fare-Class Performance &amp; Yield
          </h3>
          <div id="fareclass-graph-container" style="display: flex; flex-direction: column; gap: 0.75rem;">
            <!-- Fare class bars -->
          </div>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- 24. 👥 USER & ROLE MANAGEMENT (RBAC) -->
    <!-- =================================================================== -->
    <section id="users-tab" class="tab-content">
      <div class="hero-banner">
        <div style="display:inline-block; padding: 0.25rem 0.75rem; background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 9999px; font-size: 0.8rem; font-weight: 800; color: #fbbf24; margin-bottom: 0.5rem;">
          24. 👥 USER / ROLE MANAGEMENT
        </div>
        <h1 class="hero-title">Staff Credentials &amp; RBAC Access Governance</h1>
        <p class="hero-subtitle">
          SUPER_ADMIN controls role assignments for Operations Agents and Passenger accounts. Strict separation of operational access.
        </p>
      </div>

      <!-- Roles Legend -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
        <div class="card" style="padding: 1rem; border-top: 3px solid #fbbf24;">
          <div style="font-weight: 800; color: #fbbf24; font-size: 0.95rem;">👑 SUPER_ADMIN</div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.35rem;">
            Full administrative fleet control, seat map designer, capacity mutations, approvals, audit logs &amp; user role management.
          </div>
        </div>
        <div class="card" style="padding: 1rem; border-top: 3px solid #60a5fa;">
          <div style="font-weight: 800; color: #60a5fa; font-size: 0.95rem;">✈️ OPS_AGENT</div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.35rem;">
            Operational flight dispatch, schedule modifications, flight cancellations, waitlist promotions &amp; check-in overrides.
          </div>
        </div>
        <div class="card" style="padding: 1rem; border-top: 3px solid #94a3b8;">
          <div style="font-weight: 800; color: #94a3b8; font-size: 0.95rem;">👤 PASSENGER</div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.35rem;">
            Public booking portal, search, seat selection, waitlist entry and self-service cancellation. Restricted from admin portal.
          </div>
        </div>
      </div>

      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem;">
          <h2 class="card-title" style="margin-bottom:0;">System Users Registry</h2>
          <button class="btn btn-secondary btn-sm" onclick="loadUserManagement()">🔄 Refresh Users</button>
        </div>

        <div style="overflow-x: auto;">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="users-table-body">
              <!-- Dynamically populated from /api/v1/admin/users -->
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- 26. ⚙️ SYSTEM HEALTH & INFRASTRUCTURE MONITOR -->
    <!-- =================================================================== -->
    <section id="health-tab" class="tab-content">
      <div class="hero-banner">
        <div style="display:inline-block; padding: 0.25rem 0.75rem; background: rgba(52, 211, 153, 0.2); border: 1px solid rgba(52, 211, 153, 0.4); border-radius: 9999px; font-size: 0.8rem; font-weight: 800; color: #34d399; margin-bottom: 0.5rem;">
          26. ⚙️ SYSTEM HEALTH &amp; TELEMETRY
        </div>
        <h1 class="hero-title">System Health &amp; Automation Telemetry</h1>
        <p class="hero-subtitle">
          Real-time service health, database connections, vector database connectivity, and n8n background automation status.
        </p>
      </div>

      <!-- Health Status Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;" id="health-services-grid">
        <!-- Dynamically rendered service statuses (FastAPI, PostgreSQL, n8n, Pinecone, Gmail) -->
      </div>

      <!-- Automation Telemetry Cards -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
        <div class="card" style="padding: 1.25rem; border-left: 4px solid #34d399;">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Last Automation</div>
          <div style="font-size: 1.15rem; font-weight: 800; color: #fff; margin: 0.35rem 0;" id="health-last-auto-name">Waitlist promotion</div>
          <div style="font-size: 0.8rem; color: #34d399;" id="health-last-auto-time">🟢 2 min ago</div>
        </div>
        <div class="card" style="padding: 1.25rem; border-left: 4px solid #f87171;">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Failed Workflows</div>
          <div style="font-size: 1.8rem; font-weight: 900; color: #f87171; margin: 0.2rem 0;" id="health-failed-runs">1</div>
          <div style="font-size: 0.75rem; color: #94a3b8;">Automatic retry scheduled</div>
        </div>
        <div class="card" style="padding: 1.25rem; border-left: 4px solid #60a5fa;">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">24h Automations Executed</div>
          <div style="font-size: 1.8rem; font-weight: 900; color: #60a5fa; margin: 0.2rem 0;" id="health-total-runs">1,420</div>
          <div style="font-size: 0.75rem; color: #34d399;">Success Rate: 99.93%</div>
        </div>
      </div>

      <!-- n8n Workflows Telemetry Table -->
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem;">
          <div>
            <h2 class="card-title" style="margin-bottom:0.2rem;">n8n Workflow Automation Registry</h2>
            <div style="font-size: 0.8rem; color: var(--text-muted);">Background cron jobs, event webhooks, and retry pipelines</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="loadSystemHealth()">🔄 Refresh Telemetry</button>
        </div>

        <div style="overflow-x: auto;">
          <table class="table">
            <thead>
              <tr>
                <th>Workflow Name</th>
                <th>Status</th>
                <th>Last Run</th>
                <th>Failed Runs</th>
                <th>Retries</th>
                <th>Execution Time</th>
              </tr>
            </thead>
            <tbody id="health-workflows-tbody">
              <!-- Dynamically populated -->
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- 27. 🔄 RECONCILIATION & DATA INTEGRITY -->
    <!-- =================================================================== -->
    <section id="reconciliation-tab" class="tab-content">
      <div class="hero-banner">
        <div style="display:inline-block; padding: 0.25rem 0.75rem; background: rgba(56, 189, 248, 0.2); border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 9999px; font-size: 0.8rem; font-weight: 800; color: #38bdf8; margin-bottom: 0.5rem;">
          27. 🔄 RECONCILIATION / DATA INTEGRITY
        </div>
        <h1 class="hero-title">Transactional Cross-Ledger Reconciliation</h1>
        <p class="hero-subtitle">
          Ensures atomic consistency between FastAPI transactional state and n8n background PostgreSQL workers. Validates capacity, inventory holds, waitlist FIFO order, and refund ledgers.
        </p>
      </div>

      <!-- Integrity Scanner Card -->
      <div class="card" style="margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem;">
          <div>
            <h2 class="card-title" style="margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.5rem;">
              <span>🛡️</span> Database Integrity Status
            </h2>
            <div style="font-size: 0.82rem; color: var(--text-muted);">Cross-table consistency check between flights, seats, holds, and Stripe payments</div>
          </div>
          <button class="btn btn-primary btn-sm" onclick="runIntegrityScanner()">
            🔄 Run Full Reconciliation Scan
          </button>
        </div>

        <!-- 5 Database Integrity Items -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.25rem;" id="reconciliation-checks-grid">
          <!-- Populated from /api/v1/admin/reconciliation -->
        </div>

        <!-- Integrity Notice -->
        <div class="calc-note" style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 8px; padding: 0.85rem 1rem; font-size: 0.85rem; line-height: 1.5;">
          <b style="color: #7dd3fc;">⚙️ Architectural Requirement:</b><br/>
          FastAPI transactional core aur n8n background workers dono same PostgreSQL ledger par operate karte hain.
          Reconciliation engine concurrency conflicts, uncommitted seat locks aur orphan refund intents detect aur automatically heal karta hai.
        </div>
      </div>

      <!-- Detected Issues Card -->
      <div class="card">
        <h3 style="font-size: 1.1rem; font-weight: 800; color: #fff; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
          <span>⚠️</span> Discrepancies Requiring Administrative Action
        </h3>
        <div id="reconciliation-issues-container">
          <!-- Dynamically rendered issues with 1-click resolve -->
        </div>
      </div>
    </section>
"""

# Insert new tabs right after </section> of farerules-tab
target_after_farerules = '</section>\n\n    <!-- ==================================================================='
pos = content.find(target_after_farerules)
if pos != -1:
    content = content[:pos + len('</section>\n')] + new_tabs_html + content[pos + len('</section>\n'):]
else:
    # Alternative search
    farerules_pos = content.find('id="farerules-tab"')
    if farerules_pos != -1:
        end_sec = content.find('</section>', farerules_pos)
        content = content[:end_sec + len('</section>')] + "\n" + new_tabs_html + content[end_sec + len('</section>'):]

# 4. Add modals for Sections 19-24:
# - RAG Edit Draft modal
# - Policy View modal
# - Policy Upload modal
# - User Role Change modal
modals_html = """
    <!-- =================================================================== -->
    <!-- 19. 🤖 AI RAG DRAFT EDIT MODAL -->
    <!-- =================================================================== -->
    <div id="admin-rag-edit-modal" class="modal-overlay">
      <div class="modal-box" style="max-width: 680px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
          <div>
            <div style="font-size: 0.8rem; font-weight: 700; color: #fbbf24; text-transform: uppercase;">Human Supervisor Gate</div>
            <h2 style="font-size: 1.45rem; font-weight: 800; color: #fff; margin: 0.2rem 0 0;">
              Edit AI Customer Response
            </h2>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="closeRAGEditModal()">✕</button>
        </div>

        <div style="background: rgba(15, 23, 42, 0.7); padding: 0.85rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.85rem;">
          <div><b>Passenger:</b> <span id="rag-edit-pax-name">Ali</span> | <b>Booking:</b> <span id="rag-edit-pnr">ABC123</span> | <b>Fare:</b> <span id="rag-edit-fare">Basic Economy</span></div>
          <div style="margin-top: 0.35rem;"><b>Question:</b> <span id="rag-edit-question" style="color: #60a5fa;">Can I get a refund?</span></div>
        </div>

        <div class="form-group" style="margin-bottom: 1rem;">
          <label style="font-weight: 700; font-size: 0.85rem; margin-bottom: 0.35rem; display: block;">Supervisor Edited Response:</label>
          <textarea id="rag-edit-textarea" class="form-input" style="height: 140px; font-family: inherit; line-height: 1.5;"></textarea>
        </div>

        <input type="hidden" id="rag-edit-approval-id">

        <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
          <button type="button" class="btn btn-secondary" onclick="closeRAGEditModal()">Cancel</button>
          <button type="button" class="btn btn-primary" onclick="submitRAGEditedApproval()">Save &amp; Dispatch to Customer</button>
        </div>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- 20. 📄 POLICY DOCUMENT VIEW MODAL -->
    <!-- =================================================================== -->
    <div id="admin-policy-view-modal" class="modal-overlay">
      <div class="modal-box" style="max-width: 720px; max-height: 85vh; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 0.75rem;">
          <div>
            <div style="font-size: 0.78rem; font-weight: 700; color: #34d399; text-transform: uppercase;">Pinecone Vector Indexed Document</div>
            <h2 style="font-size: 1.45rem; font-weight: 800; color: #fff; margin: 0.2rem 0 0;" id="policy-view-title">
              Basic Economy Refund Policy
            </h2>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="closePolicyViewModal()">✕</button>
        </div>

        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; background: rgba(15, 23, 42, 0.7); padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.82rem;">
          <div><span style="color: var(--text-muted);">Fare Type:</span> <b id="policy-view-fare" style="color: #fff;">Basic Economy</b></div>
          <div><span style="color: var(--text-muted);">Effective Date:</span> <b id="policy-view-date" style="color: #fff;">01 Sep 2026</b></div>
          <div><span style="color: var(--text-muted);">Version:</span> <b id="policy-view-version" style="color: #fbbf24;">v3 (Active)</b></div>
        </div>

        <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 1.25rem; font-size: 0.88rem; line-height: 1.6; white-space: pre-wrap; font-family: monospace; color: #cbd5e1;" id="policy-view-content">
          <!-- Policy content text -->
        </div>

        <div style="text-align: right; margin-top: 1rem;">
          <button type="button" class="btn btn-secondary" onclick="closePolicyViewModal()">Close Document</button>
        </div>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- 20. 📄 POLICY UPLOAD MODAL -->
    <!-- =================================================================== -->
    <div id="admin-policy-upload-modal" class="modal-overlay">
      <div class="modal-box" style="max-width: 600px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
          <div>
            <div style="font-size: 0.8rem; font-weight: 700; color: #34d399; text-transform: uppercase;">Pinecone Ingestion Pipeline</div>
            <h2 style="font-size: 1.45rem; font-weight: 800; color: #fff; margin: 0.2rem 0 0;">Upload Policy Document</h2>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="closePolicyUploadModal()">✕</button>
        </div>

        <form onsubmit="submitPolicyUpload(event)">
          <div class="form-group" style="margin-bottom: 0.85rem;">
            <label style="font-weight: 700; font-size: 0.85rem; display: block; margin-bottom: 0.35rem;">Document Title:</label>
            <input type="text" id="upload-policy-title" class="form-input" placeholder="e.g. Flexible Fare Change & Cancellation Policy" required>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.85rem;">
            <div class="form-group">
              <label style="font-weight: 700; font-size: 0.85rem; display: block; margin-bottom: 0.35rem;">Fare Type:</label>
              <select id="upload-policy-fare" class="form-select">
                <option value="Basic Economy">Basic Economy</option>
                <option value="Standard Economy">Standard Economy</option>
                <option value="Flexible">Flexible</option>
                <option value="Business Flex">Business Flex</option>
                <option value="All Fares">All Fares (Fleet General)</option>
              </select>
            </div>
            <div class="form-group">
              <label style="font-weight: 700; font-size: 0.85rem; display: block; margin-bottom: 0.35rem;">Effective Date:</label>
              <input type="date" id="upload-policy-date" class="form-input" required>
            </div>
          </div>
          <div class="form-group" style="margin-bottom: 1.25rem;">
            <label style="font-weight: 700; font-size: 0.85rem; display: block; margin-bottom: 0.35rem;">Policy Text Content (to Chunk &amp; Embed):</label>
            <textarea id="upload-policy-text" class="form-input" style="height: 120px;" placeholder="Paste legal policy provisions here..." required></textarea>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
            <button type="button" class="btn btn-secondary" onclick="closePolicyUploadModal()">Cancel</button>
            <button type="submit" class="btn btn-primary">⚡ Ingest into Pinecone</button>
          </div>
        </form>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- 24. 👥 USER ROLE CHANGE MODAL -->
    <!-- =================================================================== -->
    <div id="admin-user-role-modal" class="modal-overlay">
      <div class="modal-box" style="max-width: 500px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
          <div>
            <div style="font-size: 0.8rem; font-weight: 700; color: #fbbf24; text-transform: uppercase;">RBAC Administration</div>
            <h2 style="font-size: 1.45rem; font-weight: 800; color: #fff; margin: 0.2rem 0 0;">Update User Role</h2>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="closeUserRoleModal()">✕</button>
        </div>

        <div style="background: rgba(15, 23, 42, 0.7); padding: 0.85rem; border-radius: 6px; margin-bottom: 1.25rem;">
          <div><b>User:</b> <span id="urm-user-name" style="color: #fff;">Ops Officer</span></div>
          <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.25rem;"><b>Email:</b> <span id="urm-user-email">ops@aerocore.com</span></div>
        </div>

        <form onsubmit="submitUserRoleChange(event)">
          <input type="hidden" id="urm-user-id">
          <div class="form-group" style="margin-bottom: 1.25rem;">
            <label style="font-weight: 700; font-size: 0.85rem; display: block; margin-bottom: 0.35rem;">Assigned Role:</label>
            <select id="urm-role-select" class="form-select">
              <option value="SUPER_ADMIN">👑 SUPER_ADMIN (Full Fleet Control)</option>
              <option value="OPS_AGENT">✈️ OPS_AGENT (Operations &amp; Dispatch)</option>
              <option value="PASSENGER">👤 PASSENGER (Customer Portal Only)</option>
            </select>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
            <button type="button" class="btn btn-secondary" onclick="closeUserRoleModal()">Cancel</button>
            <button type="submit" class="btn btn-primary">Save Role</button>
          </div>
        </form>
      </div>
    </div>
"""

# Insert modals right before </main>
end_main_pos = content.rfind('</main>')
if end_main_pos != -1:
    content = content[:end_main_pos] + modals_html + "\n      </main>\n    </div><!-- /.admin-main-area -->\n  </div><!-- /.admin-layout-root -->\n" + content[end_main_pos + len('</main>'):]

with open(admin_html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully updated frontend/admin.html with all Sections 19-28 tab views and modals!")
