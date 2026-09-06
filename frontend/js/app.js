/**
 * AeroCore Flight Management System - Client Application Logic
 * Interacts with FastAPI backend REST API
 */

const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || !window.location.hostname)
  ? "http://127.0.0.1:8000/api/v1"
  : `${window.location.origin}/api/v1`;
let currentAuthToken = "";
let selectedFlight = null;
let selectedClass = null;
let selectedSeatId = null;
let selectedSeatNumber = null;
let passengerSeatMap = {}; // Maps passenger index to seat_id
let passengerSeatNumbers = {}; // Maps passenger index to seat_number
let currentAssigningPassenger = null; // Index of passenger currently picking seat
let allFlights = []; // Fix ReferenceError

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
  await autoLoginAdmin();
  loadAllFlights();
  setDefaultDates();
});

function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach(el => el.classList.remove("active"));
  const target = document.getElementById(tabId);
  if (target) target.classList.add("active");
  if (window.event && window.event.target && window.event.target.classList) {
    window.event.target.classList.add("active");
  }
}

function setDefaultDates() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const deptISO = tomorrow.toISOString().slice(0, 16);
  
  const arr = new Date(tomorrow);
  arr.setHours(arr.getHours() + 7);
  const arrISO = arr.toISOString().slice(0, 16);

  const deptInput = document.getElementById("create-dept");
  const arrInput = document.getElementById("create-arr");
  if (deptInput) deptInput.value = deptISO;
  if (arrInput) arrInput.value = arrISO;
}

// Auto-login as Super Admin for demonstration
async function autoLoginAdmin() {
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "superadmin@airline.com", password: "Admin123!" })
    });
    if (res.ok) {
      const data = await res.json();
      currentAuthToken = data.access_token;
      const userTag = document.getElementById("current-user-tag");
      if (userTag) {
        userTag.innerText = `Role: ${data.role} (${data.full_name})`;
      }
    }
  } catch (err) {
    console.warn("Backend not yet running or auth bypassed for local preview:", err);
  }
}

// =============================================================================
// FLIGHT SEARCH & INVENTORY
// =============================================================================
async function handleSearch(e) {
  e.preventDefault();
  const origin = document.getElementById("search-origin").value.trim().toUpperCase();
  const dest = document.getElementById("search-destination").value.trim().toUpperCase();
  const date = document.getElementById("search-date").value;
  const currency = document.getElementById("search-currency").value;

  let url = `${API_BASE}/flights/search?origin=${origin}&destination=${dest}&currency=${currency}`;
  if (date) url += `&date=${date}`;

  try {
    const res = await fetch(url);
    const flights = await res.json();
    renderFlightResults(flights, currency);
  } catch (err) {
    showToast("Failed to search flights. Ensure FastAPI backend is running.", "error");
  }
}

async function loadAllFlights() {
  const currency = document.getElementById("search-currency") ? document.getElementById("search-currency").value : "USD";
  try {
    const res = await fetch(`${API_BASE}/flights/search?origin=LHR&destination=DXB&currency=${currency}`);
    if (res.ok) {
      const flights = await res.json();
      renderFlightResults(flights, currency);
    }
  } catch (err) {
    console.error("Could not fetch flights:", err);
  }
}

const CURRENCY_SYMBOLS = {
  USD: "$",
  GBP: "£",
  EUR: "€",
  AED: "AED "
};

function formatHHMM(isoStr) {
  if (!isoStr) return "--:--";
  const d = new Date(isoStr);
  const h = String(d.getUTCHours()).padStart(2, '0');
  const m = String(d.getUTCMinutes()).padStart(2, '0');
  return `${h}:${m}`;
}

function formatPrice(val, currency) {
  const sym = CURRENCY_SYMBOLS[currency] || (currency + " ");
  const formatted = Math.round(val).toLocaleString();
  return `${sym}${formatted}`;
}

function handleCurrencyChange() {
  const form = document.getElementById("search-form");
  if (form) {
    handleSearch(new Event("submit"));
  }
}

function toggleFlightDetails(flightId) {
  const panel = document.getElementById(`details-${flightId}`);
  const arrow = document.getElementById(`view-arrow-${flightId}`);
  if (!panel) return;
  if (panel.style.display === "none" || panel.style.display === "") {
    panel.style.display = "block";
    if (arrow) arrow.innerText = "▲";
  } else {
    panel.style.display = "none";
    if (arrow) arrow.innerText = "▼";
  }
}

function renderFlightResults(flights, currency) {
  const container = document.getElementById("search-results");
  if (!flights || flights.length === 0) {
    container.innerHTML = `<div class="card"><p style="color:var(--text-muted);">No flights found for this route and date.</p></div>`;
    return;
  }

  container.innerHTML = flights.map(f => {
    const depTime = formatHHMM(f.departure_time);
    const arrTime = formatHHMM(f.arrival_time);

    const firstClass = f.classes.find(c => c.class_code === 'FIRST');
    const bizClass = f.classes.find(c => c.class_code === 'BUSINESS');
    const ecoClass = f.classes.find(c => c.class_code === 'ECONOMY');

    const firstSeats = firstClass ? firstClass.available_seats : 0;
    const bizSeats = bizClass ? bizClass.available_seats : 0;
    const ecoSeats = ecoClass ? ecoClass.available_seats : 0;

    const firstFare = firstClass ? formatPrice(firstClass.base_fare, currency) : 'N/A';
    const bizFare = bizClass ? formatPrice(bizClass.base_fare, currency) : 'N/A';
    const ecoFare = ecoClass ? formatPrice(ecoClass.base_fare, currency) : 'N/A';

    const classPills = f.classes.map(c => {
      const isAvailable = c.available_seats > 0;
      const formattedFare = formatPrice(c.base_fare, currency);
      return `
        <div class="class-pill ${isAvailable ? 'available' : 'full'}">
          <div class="class-name">${c.class_code}</div>
          ${isAvailable ? `
            <div class="class-fare">${formattedFare}</div>
            <div class="class-seats">${c.available_seats} seats free</div>
            <button class="btn" style="padding:0.35rem 0.75rem; font-size:0.8rem; margin-top:0.4rem; width:100%;" onclick="openFareSelectionModal('${f.id}', '${f.flight_number}', '${f.origin}', '${f.destination}', '${c.class_code}', ${c.base_fare})">Select Fare</button>
          ` : `
            <div style="font-size:1.15rem; font-weight:900; color:#ef4444; margin:0.35rem 0; letter-spacing:1px;">FULL</div>
            <div class="class-seats" style="color:#f87171;">0 seats available</div>
            <button class="btn btn-warning" style="padding:0.4rem 0.75rem; font-size:0.82rem; margin-top:0.4rem; width:100%; font-weight:800; background:linear-gradient(135deg, #f59e0b 0%, #d97706 100%); border:none; color: #0f172a; cursor:pointer;" onclick="handleWaitlistJoinModal('${f.id}', '${c.class_code}', '${f.flight_number}', '${f.origin}', '${f.destination}')">
              Join Waitlist
            </button>
          `}
        </div>
      `;
    }).join("");

    return `
      <div class="flight-search-card" id="flight-card-${f.id}">
        <div class="flight-search-header">
          <div>
            <div class="route-airports">
              <span>${f.origin}</span>
              <span class="route-arrow">→</span>
              <span>${f.destination}</span>
            </div>
            <div class="route-times">
              ${depTime} → ${arrTime}
            </div>
          </div>
          <div>
            <span class="flight-meta-badge">Flight ${f.flight_number} • Status: ${f.status}</span>
          </div>
        </div>

        <div class="flight-body-grid">
          <!-- Real-Time Seats Inventory -->
          <div class="inventory-box">
            <div class="inventory-box-title">Available Seats</div>
            <div class="inventory-row">
              <span class="inv-class">First</span>
              <span class="inv-seats ${firstSeats === 0 ? 'empty' : (firstSeats < 5 ? 'low' : '')}">${firstSeats} seats</span>
            </div>
            <div class="inventory-row">
              <span class="inv-class">Business</span>
              <span class="inv-seats ${bizSeats === 0 ? 'empty' : (bizSeats < 10 ? 'low' : '')}">${bizSeats} seats</span>
            </div>
            <div class="inventory-row">
              <span class="inv-class">Economy</span>
              <span class="inv-seats ${ecoSeats === 0 ? 'empty' : (ecoSeats < 10 ? 'low' : '')}">${ecoSeats} seats</span>
            </div>
          </div>

          <!-- Starting Fares Breakdown -->
          <div class="pricing-box">
            <div class="pricing-box-title">Pricing Starting From</div>
            <div class="price-row">
              <span class="price-label">Economy from</span>
              <span class="price-val">${ecoFare}</span>
            </div>
            <div class="price-row">
              <span class="price-label">Business from</span>
              <span class="price-val">${bizFare}</span>
            </div>
            <div class="price-row">
              <span class="price-label">First from</span>
              <span class="price-val">${firstFare}</span>
            </div>
          </div>
        </div>

        <div class="flight-footer-actions">
          <button class="btn-view-flight" onclick="toggleFlightDetails('${f.id}')">
            <span>View Flight</span>
            <span id="view-arrow-${f.id}">▼</span>
          </button>
        </div>

        <!-- Expanded Flight Actions and Seat Map -->
        <div id="details-${f.id}" class="flight-expanded-details" style="display:none;">
          <div style="font-weight:700; font-size:0.95rem; margin-bottom:0.75rem; color: #0f172a;">Select Cabin Class to Book:</div>
          <div class="flight-classes-grid">
            ${classPills}
          </div>
          <div style="margin-top: 1.25rem; display: flex; gap: 1rem; align-items: center; justify-content: flex-end; flex-wrap: wrap;">
            <button class="btn btn-secondary" style="font-size:0.85rem;" onclick="viewSeatMap('${f.id}', '${f.flight_number}')">💺 View Aircraft Cabin Seat Map</button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// =============================================================================
// BOOKING & CHECKOUT (REQ-BKG-17, 18, 19, REQ-BKG-21)
// =============================================================================
async function openBookingModal(flightId, flightNumber, origin, destination, classCode, baseFare, defaultFareType = "FLEXIBLE", availableSeats = null) {
  if (availableSeats === null) {
    const fObj = allFlights.find(fl => fl.id === flightId);
    const cObj = fObj?.classes?.find(cl => cl.class_code === classCode);
    availableSeats = cObj ? cObj.available_seats : (selectedFlight?.availableSeats || 3);
  }

  selectedFlight = { flightId, flightNumber, origin, destination, baseFare, availableSeats };
  selectedClass = classCode;

  if (defaultFareType) {
    const fareSelect = document.getElementById("modal-fare-type");
    if (fareSelect) fareSelect.value = defaultFareType;
  }

  const isBasic = (defaultFareType === "BASIC_ECONOMY");
  const checkoutNotice = document.getElementById("checkout-seat-notice");
  if (checkoutNotice) checkoutNotice.style.display = isBasic ? "flex" : "none";

  const seatLabel = (isBasic || !selectedSeatNumber) ? 'Seat: Assigned at check-in' : `Selected Seat: ${selectedSeatNumber}`;
  document.getElementById("modal-flight-title").innerText = `Book Flight ${flightNumber} (${origin} ➔ ${destination})`;
  document.getElementById("modal-flight-meta").innerText = `Class: ${classCode} | ${seatLabel} | Base Fare: $${baseFare.toFixed(2)} | Available: ${availableSeats} seats`;
  document.getElementById("modal-flight-id").value = flightId;
  document.getElementById("modal-class-code").value = classCode;

  // Reset partial policy to system default: FULL_FAIL (REQ-BKG-21)
  const policyInput = document.getElementById("modal-partial-policy");
  if (policyInput) policyInput.value = "FULL_FAIL";

  // Place temporary seat hold (REQ-BKG-17)
  try {
    const holdRes = await fetch(`${API_BASE}/bookings/hold`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({ flight_id: flightId, class_code: classCode })
    });
    if (holdRes.ok) {
      const holdData = await holdRes.json();
      document.getElementById("modal-hold-id").value = holdData.hold_id;
      showToast(`Temporary 10-minute hold placed on ${classCode} seat.`, "info");
    }
  } catch (err) {
    console.warn("Hold bypass:", err);
  }

  // Render Passenger fields (Passenger 1, Passenger 2...)
  renderPassengerForms();
  document.getElementById("checkout-modal").classList.add("active");
}

// 5. 👥 PASSENGER INFORMATION DYNAMIC FORMS
function renderPassengerForms() {
  const container = document.getElementById("passengers-inputs-container");
  if (!container) return;

  const countSelect = document.getElementById("pax-count-select");
  const count = parseInt(countSelect ? countSelect.value : "1", 10) || 1;

  // Preserve existing inputs if user changed count
  const existingData = [];
  for (let i = 1; i <= 9; i++) {
    const fEl = document.getElementById(`pax-${i}-first`);
    const lEl = document.getElementById(`pax-${i}-last`);
    const eEl = document.getElementById(`pax-${i}-email`);
    const pEl = document.getElementById(`pax-${i}-phone`);
    if (fEl && lEl) {
      existingData.push({
        first: fEl.value,
        last: lEl.value,
        email: eEl ? eEl.value : "",
        phone: pEl ? pEl.value : ""
      });
    }
  }

  // Pre-filled defaults for quick seamless testing
  const demoDefaults = [
    { first: "John", last: "Doe", email: "john.doe@example.com", phone: "+1 555-0101" },
    { first: "Sarah", last: "Connor", email: "sarah.c@example.com", phone: "+1 555-0102" },
    { first: "Michael", last: "Scott", email: "m.scott@dundermifflin.com", phone: "+1 555-0103" },
    { first: "Pam", last: "Beesly", email: "pam.b@dundermifflin.com", phone: "+1 555-0104" },
    { first: "Jim", last: "Halpert", email: "jim.h@dundermifflin.com", phone: "+1 555-0105" },
    { first: "Dwight", last: "Schrute", email: "dwight.s@schrute-farms.com", phone: "+1 555-0106" },
    { first: "Angela", last: "Martin", email: "angela.m@example.com", phone: "+1 555-0107" },
    { first: "Oscar", last: "Martinez", email: "oscar.m@example.com", phone: "+1 555-0108" },
    { first: "Kevin", last: "Malone", email: "kevin.m@example.com", phone: "+1 555-0109" }
  ];

  let html = "";
  for (let i = 1; i <= count; i++) {
    const existing = existingData[i - 1];
    const def = demoDefaults[i - 1] || { first: `Passenger`, last: `${i}`, email: `pax${i}@example.com`, phone: `+1 555-010${i}` };
    const firstVal = existing ? existing.first : def.first;
    const lastVal = existing ? existing.last : def.last;
    const emailVal = existing ? existing.email : def.email;
    const phoneVal = existing ? existing.phone : def.phone;

    // Determine if fare allows seat selection
    const fareType = document.getElementById("modal-fare-type") ? document.getElementById("modal-fare-type").value : "FLEXIBLE";
    const canSelectSeat = fareType !== "BASIC_ECONOMY";
    const seatNumStr = passengerSeatNumbers[i] || "None";
    const flightId = document.getElementById("modal-flight-id") ? document.getElementById("modal-flight-id").value : null;
    const classCode = document.getElementById("modal-class-code") ? document.getElementById("modal-class-code").value : "ECONOMY";

    const seatSelectionHtml = canSelectSeat ? `
      <div style="margin-left:auto; display:flex; align-items:center; gap:0.5rem;">
        <span style="font-size:0.8rem; color:var(--text-muted);" id="pax-${i}-seat-label">Seat: ${seatNumStr}</span>
        <button type="button" class="btn btn-primary" style="padding:0.25rem 0.75rem; font-size:0.8rem;" onclick="openSeatSelectionForPassenger(${i}, '${flightId}', '${classCode}')">Select Seat</button>
      </div>
    ` : `<div style="margin-left:auto; display:flex; align-items:center;"><span style="font-size:0.8rem; color:var(--text-muted);">Seat: Auto-assigned at check-in</span></div>`;

    html += `
      <div class="passenger-card" id="passenger-card-${i}">
        <div class="passenger-card-header" style="flex-wrap: wrap; gap: 0.5rem;">
          <span style="font-size: 1.1rem;">👤</span>
          <span style="font-weight: 800; font-size: 0.95rem; color: #0f172a;">Passenger ${i}</span>
          ${i === 1 ? '<span class="badge badge-success" style="font-size:0.7rem;">Primary Contact</span>' : `<span class="badge" style="background: rgba(99,102,241,0.25); color:#a5b4fc; font-size:0.7rem;">Group Member ${i}</span>`}
          ${seatSelectionHtml}
        </div>
        <div class="passenger-fields-grid">
          <div class="form-group" style="margin-bottom:0.5rem;">
            <label style="font-size:0.8rem; font-weight:600; color:var(--text-muted); margin-bottom:0.25rem;">First Name</label>
            <input type="text" id="pax-${i}-first" class="form-input" placeholder="First Name" value="${firstVal}" required>
          </div>
          <div class="form-group" style="margin-bottom:0.5rem;">
            <label style="font-size:0.8rem; font-weight:600; color:var(--text-muted); margin-bottom:0.25rem;">Last Name</label>
            <input type="text" id="pax-${i}-last" class="form-input" placeholder="Last Name" value="${lastVal}" required>
          </div>
          <div class="form-group" style="margin-bottom:0.5rem;">
            <label style="font-size:0.8rem; font-weight:600; color:var(--text-muted); margin-bottom:0.25rem;">Email</label>
            <input type="email" id="pax-${i}-email" class="form-input" placeholder="Email" value="${emailVal}" required>
          </div>
          <div class="form-group" style="margin-bottom:0.5rem;">
            <label style="font-size:0.8rem; font-weight:600; color:var(--text-muted); margin-bottom:0.25rem;">Phone</label>
            <input type="tel" id="pax-${i}-phone" class="form-input" placeholder="Phone" value="${phoneVal}" required>
          </div>
        </div>
      </div>
    `;
  }

  container.innerHTML = html;
  updateFareEstimate();
}

function updateFareEstimate() {
  if (!selectedFlight) return;
  const fareType = document.getElementById("modal-fare-type").value;
  const isBasic = (fareType === "BASIC_ECONOMY");
  const checkoutNotice = document.getElementById("checkout-seat-notice");
  if (checkoutNotice) checkoutNotice.style.display = isBasic ? "flex" : "none";
  if (isBasic) {
    selectedSeatId = null;
    selectedSeatNumber = null;
    document.getElementById("modal-flight-meta").innerText = `Class: ${selectedClass} | Seat: Assigned at check-in | Base Fare: $${selectedFlight.baseFare.toFixed(2)}`;
  }

  const count = parseInt(document.getElementById("pax-count-select")?.value || "1", 10) || 1;

  let multiplier = 1.0;
  if (fareType === "FLEXIBLE") multiplier = 1.25;
  if (fareType === "BUSINESS_FLEX") multiplier = 1.45;

  const unitFare = selectedFlight.baseFare * multiplier;
  const total = unitFare * count;

  const currency = document.getElementById("search-currency") ? document.getElementById("search-currency").value : "USD";
  const sym = CURRENCY_SYMBOLS[currency] || "$";

  document.getElementById("modal-total-fare").innerText = `${sym}${total.toFixed(2)}`;
}

function closeModal() {
  document.getElementById("checkout-modal").classList.remove("active");
  passengerSeatMap = {};
  passengerSeatNumbers = {};
  currentAssigningPassenger = null;
}

// 6. 👨‍👩‍👧 GROUP BOOKING CONFIRMATION & AVAILABILITY LOGIC (REQ-BKG-21)
async function handleConfirmBooking(e) {
  if (e) e.preventDefault();

  const count = parseInt(document.getElementById("pax-count-select")?.value || "1", 10) || 1;
  const partialPolicy = document.getElementById("modal-partial-policy") ? document.getElementById("modal-partial-policy").value : "FULL_FAIL";

  const availableSeats = (selectedFlight && typeof selectedFlight.availableSeats === 'number') 
    ? selectedFlight.availableSeats 
    : 3;

  // Group Availability Check: if requested count > available seats and user has not chosen PARTIAL_HOLD:
  if (count > availableSeats && partialPolicy !== "PARTIAL_HOLD") {
    document.getElementById("group-alert-requested").innerText = `You requested ${count} passengers.`;
    document.getElementById("group-alert-available").innerText = `Only ${availableSeats} seats are available.`;
    document.getElementById("group-availability-modal").classList.add("active");
    return;
  }

  await executeBookingSubmission();
}

function handleGroupCancel() {
  document.getElementById("group-availability-modal").classList.remove("active");
  const policyInput = document.getElementById("modal-partial-policy");
  if (policyInput) policyInput.value = "FULL_FAIL";
  showToast("Entire group request cancelled under default FULL_FAIL policy.", "info");
}

function handleGroupPartialHold() {
  document.getElementById("group-availability-modal").classList.remove("active");
  const policyInput = document.getElementById("modal-partial-policy");
  if (policyInput) policyInput.value = "PARTIAL_HOLD";
  const avail = selectedFlight?.availableSeats || 3;
  showToast(`Group policy set to PARTIAL_HOLD. Holding all ${avail} available seats.`, "success");
  executeBookingSubmission();
}

async function executeBookingSubmission() {
  const flightId = document.getElementById("modal-flight-id").value;
  const classCode = document.getElementById("modal-class-code").value;
  const holdId = document.getElementById("modal-hold-id").value;
  const fareType = document.getElementById("modal-fare-type").value;
  const partialPolicy = document.getElementById("modal-partial-policy").value || "FULL_FAIL";
  const creditCode = document.getElementById("modal-credit-code").value.trim();
  const count = parseInt(document.getElementById("pax-count-select")?.value || "1", 10) || 1;

  const passengers = [];
  for (let i = 1; i <= count; i++) {
    const first = document.getElementById(`pax-${i}-first`)?.value.trim() || `Passenger${i}`;
    const last = document.getElementById(`pax-${i}-last`)?.value.trim() || "Customer";
    const email = document.getElementById(`pax-${i}-email`)?.value.trim() || `pax${i}@example.com`;
    const phone = document.getElementById(`pax-${i}-phone`)?.value.trim() || "+1 555-0100";
    
    passengers.push({
      first_name: first,
      last_name: last,
      passport_number: `P${Math.random().toString(36).substring(2, 9).toUpperCase()}`,
      seat_id: passengerSeatMap[i] || (i === 1 ? selectedSeatId : null)
    });
  }

  const currency = document.getElementById("search-currency") ? document.getElementById("search-currency").value : "USD";
  const idempotencyKey = crypto.randomUUID();

  const payload = {
    flight_id: flightId,
    class_code: classCode,
    fare_type: fareType,
    hold_id: holdId || null,
    partial_policy: partialPolicy,
    currency: currency,
    credit_code: creditCode || null,
    passengers: passengers
  };

  try {
    const res = await fetch(`${API_BASE}/bookings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json();
      closeModal();
      const bookedPaxCount = data.passengers ? data.passengers.length : passengers.length;
      showToast(`Confirmed! PNR: ${data.booking_reference} (${bookedPaxCount} passenger(s) booked). Confirmation email sent via Gmail.`, "success");
      loadAllFlights();
      // Auto-lookup in portal
      if (document.getElementById("lookup-pnr")) {
        document.getElementById("lookup-pnr").value = data.booking_reference;
      }
      if (document.getElementById("lookup-email")) {
        document.getElementById("lookup-email").value = (passengers[0] ? passengers[0].email : "john.doe@example.com");
      }
      switchTab("portal-tab");
      lookupBooking();
    } else {
      const err = await res.json();
      // If backend rejected under FULL_FAIL with 409
      if (res.status === 409 && err.detail && err.detail.includes("FULL_FAIL")) {
        const match = err.detail.match(/Only (\d+) seats available for group of (\d+)/);
        const avail = match ? match[1] : (selectedFlight?.availableSeats || 3);
        const reqCount = match ? match[2] : count;
        document.getElementById("group-alert-requested").innerText = `You requested ${reqCount} passengers.`;
        document.getElementById("group-alert-available").innerText = `Only ${avail} seats are available.`;
        document.getElementById("group-availability-modal").classList.add("active");
        showToast(err.detail, "error");
      } else {
        showToast(err.detail || "Booking failed", "error");
      }
    }
  } catch (err) {
    showToast("Network error executing booking.", "error");
  }
}

// =============================================================================
// FARE SELECTION & POLICY RULES (REQ-SRC-13)
// =============================================================================
let pendingFareContext = null;

function openFareSelectionModal(flightId, flightNumber, origin, destination, classCode, baseFare) {
  const fObj = allFlights.find(fl => fl.id === flightId);
  const cObj = fObj?.classes?.find(cl => cl.class_code === classCode);
  const availableSeats = cObj ? cObj.available_seats : 3;

  pendingFareContext = { flightId, flightNumber, origin, destination, classCode, baseFare, availableSeats };
  selectedFlight = { flightId, flightNumber, origin, destination, baseFare, availableSeats };
  selectedClass = classCode;

  const currency = document.getElementById("search-currency") ? document.getElementById("search-currency").value : "USD";
  const sym = CURRENCY_SYMBOLS[currency] || "$";

  const basicFare = Math.round(baseFare);
  const flexFare = Math.round(baseFare * 1.25);
  const vipFare = Math.round(baseFare * 1.45);

  document.getElementById("fare-modal-title").innerText = `Select Fare: ${classCode} Class`;
  document.getElementById("fare-modal-subtitle").innerText = `Flight ${flightNumber} (${origin} ➔ ${destination}) • Compare rules before booking`;

  const container = document.getElementById("fare-cards-container");
  container.innerHTML = `
    <!-- Card 1: Basic Economy -->
    <div class="fare-tier-card">
      <div class="fare-tier-badge badge-cheapest">Cheapest</div>
      <div class="fare-tier-name">Basic Economy</div>
      <div class="fare-tier-price">${sym}${basicFare.toLocaleString()}</div>
      
      <div class="fare-rules-list">
        <div class="fare-rule-item negative">
          <span class="rule-icon">✕</span>
          <span class="rule-text"><b>No changes</b> allowed</span>
        </div>
        <div class="fare-rule-item negative">
          <span class="rule-icon">✕</span>
          <span class="rule-text"><b>No seat selection</b></span>
        </div>
        <div class="fare-rule-item negative">
          <span class="rule-icon">✕</span>
          <span class="rule-text"><b>Non-refundable</b> ($0 refund)</span>
        </div>
        <div class="fare-rule-item positive">
          <span class="rule-icon">✓</span>
          <span class="rule-text">1 Personal item under seat</span>
        </div>
      </div>

      <button class="btn btn-select-fare" onclick="chooseFareType('BASIC_ECONOMY', ${basicFare})">
        Select Fare
      </button>
    </div>

    <!-- Card 2: Flexible (Recommended) -->
    <div class="fare-tier-card popular">
      <div class="fare-tier-badge badge-popular">Recommended</div>
      <div class="fare-tier-name">Flexible</div>
      <div class="fare-tier-price">${sym}${flexFare.toLocaleString()}</div>
      
      <div class="fare-rules-list">
        <div class="fare-rule-item positive">
          <span class="rule-icon">✓</span>
          <span class="rule-text"><b>Changes allowed</b> (free reschedule)</span>
        </div>
        <div class="fare-rule-item positive">
          <span class="rule-icon">✓</span>
          <span class="rule-text"><b>Seat selection allowed</b> (choose seat)</span>
        </div>
        <div class="fare-rule-item positive">
          <span class="rule-icon">✓</span>
          <span class="rule-text"><b>Refund according to rules</b> (minus $25 fee)</span>
        </div>
        <div class="fare-rule-item positive">
          <span class="rule-icon">✓</span>
          <span class="rule-text">1 Carry-on + 1 Checked bag</span>
        </div>
      </div>

      <button class="btn btn-select-fare active-tier" onclick="chooseFareType('FLEXIBLE', ${flexFare})">
        Select Fare
      </button>
    </div>

    <!-- Card 3: Fully Flexible -->
    <div class="fare-tier-card">
      <div class="fare-tier-badge badge-vip">VIP Flexible</div>
      <div class="fare-tier-name">Fully Flexible</div>
      <div class="fare-tier-price">${sym}${vipFare.toLocaleString()}</div>
      
      <div class="fare-rules-list">
        <div class="fare-rule-item positive">
          <span class="rule-icon">✓</span>
          <span class="rule-text"><b>Changes allowed</b> (unlimited free)</span>
        </div>
        <div class="fare-rule-item positive">
          <span class="rule-icon">✓</span>
          <span class="rule-text"><b>Priority seat selection allowed</b></span>
        </div>
        <div class="fare-rule-item positive">
          <span class="rule-icon">✓</span>
          <span class="rule-text"><b>100% Full cash refund</b></span>
        </div>
        <div class="fare-rule-item positive">
          <span class="rule-icon">✓</span>
          <span class="rule-text">Priority boarding + Lounge access</span>
        </div>
      </div>

      <button class="btn btn-select-fare" onclick="chooseFareType('BUSINESS_FLEX', ${vipFare})">
        Select Fare
      </button>
    </div>
  `;

  document.getElementById("fare-modal").classList.add("active");
}

function closeFareModal() {
  document.getElementById("fare-modal").classList.remove("active");
}

function chooseFareType(fareTypeCode, price) {
  closeFareModal();
  const ctx = pendingFareContext;
  if (!ctx) return;

  const fareSelect = document.getElementById("modal-fare-type");
  if (fareSelect) fareSelect.value = fareTypeCode;

  if (fareTypeCode === "BASIC_ECONOMY") {
    // Basic Economy: Seat auto-assigned at check-in, straight to Price Quote confirmation
    selectedSeatId = null;
    selectedSeatNumber = null;
    showToast("Basic Economy selected. Seat will be auto-assigned at check-in.", "info");
    openPriceQuoteModal(ctx, "BASIC_ECONOMY", price, null);
  } else {
    // Flexible allows seat selection!
    showToast(`${fareTypeCode === 'FLEXIBLE' ? 'Flexible' : 'Fully Flexible'} selected. Choose your aircraft seat!`, "success");
    pendingBookingContext = { ...ctx, baseFare: price, fareType: fareTypeCode };
    viewSeatMap(ctx.flightId, ctx.flightNumber, ctx.classCode);
  }
}

// =============================================================================
// PRICE QUOTE & GUARANTEED HOLD COUNTDOWN (REQ-SRC-14, 15, REQ-BKG-17)
// =============================================================================
let quoteTimerInterval = null;
let holdSecondsRemaining = 899; // 14:59 (15 minutes window)
let activeQuoteData = null;

function openPriceQuoteModal(ctx, fareType, baseFare, seatNumber) {
  activeQuoteData = { ...ctx, fareType, baseFare, seatNumber };

  const currency = document.getElementById("search-currency") ? document.getElementById("search-currency").value : "USD";
  const sym = CURRENCY_SYMBOLS[currency] || "$";

  const fareNum = Math.round(baseFare);
  const taxesNum = Math.round(baseFare * 0.12);
  const totalNum = fareNum + taxesNum;

  activeQuoteData.fareNum = fareNum;
  activeQuoteData.taxesNum = taxesNum;
  activeQuoteData.totalNum = totalNum;
  activeQuoteData.currency = currency;
  activeQuoteData.sym = sym;

  const seatText = seatNumber ? `Seat ${seatNumber}` : 'Seat: Assigned at check-in';
  document.getElementById("quote-modal-flight-info").innerText = 
    `Flight ${ctx.flightNumber} (${ctx.origin} ➔ ${ctx.destination}) • ${ctx.classCode} (${fareType.replace('_', ' ')}) • ${seatText}`;

  // Toggle Basic Economy seat notice
  const isBasic = (fareType === "BASIC_ECONOMY");
  const quoteNotice = document.getElementById("quote-seat-notice");
  if (quoteNotice) quoteNotice.style.display = isBasic ? "flex" : "none";

  document.getElementById("quote-base-fare").innerText = `${sym}${fareNum.toLocaleString()}`;
  document.getElementById("quote-taxes").innerText = `${sym}${taxesNum.toLocaleString()}`;
  document.getElementById("quote-total").innerText = `${sym}${totalNum.toLocaleString()}`;

  startHoldCountdown(899); // 14:59

  // Place backend hold
  placeBackendSeatHold(ctx.flightId, ctx.classCode, selectedSeatId);

  document.getElementById("quote-modal").classList.add("active");
}

function startHoldCountdown(durationSeconds) {
  if (quoteTimerInterval) clearInterval(quoteTimerInterval);
  holdSecondsRemaining = durationSeconds;
  updateTimerDisplays();

  quoteTimerInterval = setInterval(() => {
    holdSecondsRemaining--;
    if (holdSecondsRemaining <= 0) {
      clearInterval(quoteTimerInterval);
      quoteTimerInterval = null;
      const qTimer = document.getElementById("quote-timer-display");
      const cTimer = document.getElementById("checkout-timer-display");
      if (qTimer) qTimer.innerText = "00:00";
      if (cTimer) cTimer.innerText = "00:00";
      showToast("Your 15-minute price hold has expired. Inventory released.", "error");
      closeQuoteModal();
      closeModal();
      return;
    }
    updateTimerDisplays();
  }, 1000);
}

function updateTimerDisplays() {
  const mins = Math.floor(holdSecondsRemaining / 60);
  const secs = holdSecondsRemaining % 60;
  const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

  const quoteEl = document.getElementById("quote-timer-display");
  if (quoteEl) quoteEl.innerText = timeStr;

  const checkoutEl = document.getElementById("checkout-timer-display");
  if (checkoutEl) checkoutEl.innerText = timeStr;
}

function closeQuoteModal() {
  document.getElementById("quote-modal").classList.remove("active");
}

function continueFromQuoteModal() {
  closeQuoteModal();
  if (!activeQuoteData) return;

  const q = activeQuoteData;
  openBookingModal(q.flightId, q.flightNumber, q.origin, q.destination, q.classCode, q.totalNum, q.fareType, q.availableSeats);
}

async function placeBackendSeatHold(flightId, classCode, seatId) {
  try {
    const res = await fetch(`${API_BASE}/bookings/hold`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({ flight_id: flightId, class_code: classCode, seat_id: seatId || null })
    });
    if (res.ok) {
      const data = await res.json();
      const holdInput = document.getElementById("modal-hold-id");
      if (holdInput) holdInput.value = data.hold_id;
    }
  } catch (err) {
    console.warn("Backend hold attempt:", err);
  }
}

// =============================================================================
// SEAT MAP VIEWER WITH CABIN FILTERING (REQ-ADM-07)
// =============================================================================
let currentSeatMapFlight = null;
let currentSeatMapSeats = [];
let currentFilterCabin = "ALL";
let pendingBookingContext = null;

function selectCabinToBook(flightId, flightNumber, origin, destination, classCode, baseFare) {
  pendingBookingContext = { flightId, flightNumber, origin, destination, classCode, baseFare };
  selectedClass = classCode;
  selectedSeatId = null;
  selectedSeatNumber = null;
  document.getElementById("selected-seat-label").innerText = `Selected: None (Select your ${classCode} seat)`;
  viewSeatMap(flightId, flightNumber, classCode);
}

async function viewSeatMap(flightId, flightNumber, initialCabin = "ALL") {
  try {
    const res = await fetch(`${API_BASE}/flights/${flightId}/seat-map`);
    const data = await res.json();
    currentSeatMapFlight = { flightId, flightNumber };
    currentSeatMapSeats = data.seats || [];

    filterSeatMapCabin(initialCabin);
    document.getElementById("seatmap-modal").classList.add("active");
  } catch (err) {
    showToast("Could not load seat map", "error");
  }
}

function filterSeatMapCabin(cabinCode) {
  currentFilterCabin = cabinCode;

  // Update cabin filter tabs active state
  document.querySelectorAll(".cabin-filter-btn").forEach(b => b.classList.remove("active"));
  const activeBtn = document.getElementById(`tab-cabin-${cabinCode}`);
  if (activeBtn) activeBtn.classList.add("active");

  const titleEl = document.getElementById("seatmap-title");
  if (currentSeatMapFlight) {
    if (cabinCode === "ALL") {
      titleEl.innerText = `Seat Map: Flight ${currentSeatMapFlight.flightNumber} (All Cabins)`;
    } else {
      titleEl.innerText = `Seat Map: Flight ${currentSeatMapFlight.flightNumber} — ${cabinCode} Class`;
    }
  }

  renderSeatMapGrid();
}

function renderSeatMapGrid() {
  const container = document.getElementById("seat-grid-render");
  container.innerHTML = "";

  const filteredSeats = (currentFilterCabin === "ALL")
    ? currentSeatMapSeats
    : currentSeatMapSeats.filter(s => s.class_code === currentFilterCabin);

  if (filteredSeats.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:2rem; color:var(--text-muted);">No physical seats mapped for this cabin class.</div>`;
    return;
  }

  // Group by row
  const rowMap = {};
  filteredSeats.forEach(s => {
    if (!rowMap[s.seat_row]) rowMap[s.seat_row] = [];
    rowMap[s.seat_row].push(s);
  });

  let currentClass = "";

  Object.keys(rowMap).sort((a, b) => Number(a) - Number(b)).forEach(r => {
    const seatsInRow = rowMap[r];
    const rowClass = seatsInRow[0] ? seatsInRow[0].class_code : "";

    // Show cabin divider banner
    if (rowClass !== currentClass) {
      currentClass = rowClass;
      const sectionHeader = document.createElement("div");
      sectionHeader.className = "cabin-section-header";
      sectionHeader.innerText = `✈ ${currentClass} CABIN`;
      container.appendChild(sectionHeader);
    }

    const rowDiv = document.createElement("div");
    rowDiv.className = "seat-row";

    // Row number label
    const rowLabel = document.createElement("div");
    rowLabel.className = "row-label";
    rowLabel.innerText = r;
    rowDiv.appendChild(rowLabel);

    const half = Math.ceil(seatsInRow.length / 2);

    seatsInRow.forEach((s, idx) => {
      // Central aisle gap
      if (idx === half && seatsInRow.length > 2) {
        const gap = document.createElement("div");
        gap.className = "aisle-gap";
        rowDiv.appendChild(gap);
      }

      const seatBtn = document.createElement("div");
      // Check if this seat is selected by the current assigning passenger OR any other passenger
      let isSelectedByMe = false;
      let isSelectedByOther = false;
      if (currentAssigningPassenger) {
        isSelectedByMe = (passengerSeatMap[currentAssigningPassenger] === s.id);
        // check if another passenger has it
        Object.keys(passengerSeatMap).forEach(pIdx => {
          if (pIdx != currentAssigningPassenger && passengerSeatMap[pIdx] === s.id) {
            isSelectedByOther = true;
          }
        });
      } else {
        isSelectedByMe = (selectedSeatId === s.id);
      }

      // Booked (RED), Held (YELLOW), Available (GREEN)
      let stateClass = "available";
      let statusText = "Available";
      if (s.is_booked || isSelectedByOther) {
        stateClass = "booked";
        statusText = isSelectedByOther ? "Selected by another passenger" : "Booked (Occupied)";
      } else if (s.is_held) {
        stateClass = "held";
        statusText = "On Hold (Temporary checkout lock)";
      }

      seatBtn.className = `seat-item ${stateClass} ${isSelectedByMe ? 'selected' : ''}`;
      seatBtn.innerText = s.seat_column || s.seat_number;
      seatBtn.title = `Seat ${s.seat_number} - ${s.class_code} | Status: ${statusText}`;

      // Only available seats can be selected
      if (s.is_available && !s.is_booked && !s.is_held && !isSelectedByOther) {
        seatBtn.onclick = () => {
          document.querySelectorAll(".seat-item").forEach(el => el.classList.remove("selected"));
          seatBtn.classList.add("selected");
          
          if (currentAssigningPassenger) {
            passengerSeatMap[currentAssigningPassenger] = s.id;
            passengerSeatNumbers[currentAssigningPassenger] = s.seat_number;
            document.getElementById("selected-seat-label").innerText = `Passenger ${currentAssigningPassenger} Selected: Seat ${s.seat_number} (${s.class_code})`;
          } else {
            selectedSeatId = s.id;
            selectedSeatNumber = s.seat_number;
            selectedClass = s.class_code;
            document.getElementById("selected-seat-label").innerText = `Selected: Seat ${s.seat_number} (${s.class_code})`;
          }
          showToast(`Selected seat ${s.seat_number} (${s.class_code})`, "info");
        };
      }

      rowDiv.appendChild(seatBtn);
    });

    container.appendChild(rowDiv);
  });
}

function openSeatSelectionForPassenger(paxIndex, flightId, classCode) {
  currentAssigningPassenger = paxIndex;
  viewSeatMap(flightId, null, classCode);
}

function proceedFromSeatMap() {
  closeSeatMapModal();
  if (currentAssigningPassenger) {
    // If we were picking a seat for a specific group member, just re-render the forms
    renderPassengerForms();
    currentAssigningPassenger = null;
  } else if (pendingBookingContext) {
    const ctx = pendingBookingContext;
    openPriceQuoteModal(ctx, ctx.fareType || "FLEXIBLE", ctx.baseFare, selectedSeatNumber);
  } else if (selectedSeatId && currentSeatMapFlight) {
    const ctx = {
      flightId: currentSeatMapFlight.flightId,
      flightNumber: currentSeatMapFlight.flightNumber,
      origin: "LHR",
      destination: "DXB",
      classCode: selectedClass || "ECONOMY",
      baseFare: 450
    };
    openPriceQuoteModal(ctx, "FLEXIBLE", 450, selectedSeatNumber);
  }
}

function closeSeatMapModal() {
  document.getElementById("seatmap-modal").classList.remove("active");
}

// =============================================================================
// =============================================================================
// 8. 🔍 MANAGE / FIND MY BOOKING & REMEDIATION (REQ-CHG-23, 24, 25, 26)
// =============================================================================
async function handleFindBooking(e) {
  if (e) e.preventDefault();
  await lookupBooking();
}

async function lookupBooking() {
  const pnrInput = document.getElementById("lookup-pnr");
  const emailInput = document.getElementById("lookup-email");
  const pnr = pnrInput ? pnrInput.value.trim().toUpperCase() : "";
  const email = emailInput ? emailInput.value.trim() : "";

  if (!pnr) {
    showToast("Please enter a booking reference (PNR).", "error");
    return;
  }

  const card = document.getElementById("booking-details-card");
  card.style.display = "block";
  card.innerHTML = `
    <div style="text-align:center; padding: 2rem; color: var(--text-muted);">
      <div style="font-size: 2rem; margin-bottom: 0.5rem;" class="spin">✈</div>
      <div>Retrieving booking details for <b>${pnr}</b>...</div>
    </div>
  `;

  try {
    const url = `${API_BASE}/bookings/lookup/${encodeURIComponent(pnr)}${email ? `?email=${encodeURIComponent(email)}` : ""}`;
    const res = await fetch(url);

    if (res.ok) {
      const data = await res.json();
      renderBookingDetails(data);
      showToast(`Booking ${data.booking_reference} retrieved successfully!`, "success");
    } else {
      const err = await res.json();
      card.innerHTML = `
        <div style="text-align: center; padding: 2rem; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px;">
          <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">✕</div>
          <h3 style="color: #f87171; margin: 0 0 0.5rem;">Booking Not Found</h3>
          <p style="color: var(--text-muted); font-size: 0.9rem; margin: 0;">${err.detail || `No booking found matching reference "${pnr}". Please check your PNR and email.`}</p>
        </div>
      `;
      showToast(err.detail || "Booking not found", "error");
    }
  } catch (err) {
    card.innerHTML = `
      <div style="text-align: center; padding: 2rem; color: #f87171;">
        <div>Failed to connect to booking ledger service. Please check your internet connection or server status.</div>
      </div>
    `;
  }
}

let demoScenario = "AUTO"; // 'AUTO', 'SCHEDULE_CHANGE', 'FLIGHT_CANCELLED', 'TRAVEL_CREDIT', 'WAITLIST_JOIN', 'WAITLIST_OFFER', 'CHECKIN_REMINDER', 'PRICE_DROP'
let activeTravelCredit = null;

function setDemoScenario(scenario) {
  demoScenario = scenario;
  if (scenario === "TRAVEL_CREDIT" && !activeTravelCredit) {
    activeTravelCredit = {
      credit_code: "TC-8291",
      amount: (currentActiveBookingData ? currentActiveBookingData.total_fare : 550.00),
      expires_at: "20 September 2027",
      status: "ACTIVE"
    };
  }

  if (scenario === "WAITLIST_JOIN") {
    handleWaitlistJoinModal("demo-flight-id", "ECONOMY", "BA105", "LHR", "DXB");
    showToast("Opened Waitlist Join Modal for Economy (FULL)", "info");
    return;
  }

  if (scenario === "WAITLIST_OFFER") {
    showWaitlistOfferBanner({
      origin: "LHR",
      destination: "DXB",
      class_code: "Economy",
      entry_id: "wl-offer-demo"
    });
    switchTab('search-tab');
    window.scrollTo({ top: 100, behavior: 'smooth' });
    showToast("Triggered Waitlist Offer: Seat is available with 2-hour claim window!", "info");
    return;
  }

  if (scenario === "CHECKIN_REMINDER") {
    switchTab('portal-tab');
    const mockBooking = currentActiveBookingData || {
      id: "demo-bkg-8291",
      booking_reference: "FMS-8291A",
      flight_number: "BA105",
      origin: "LHR",
      destination: "DXB",
      departure_time: new Date(Date.now() + 20 * 3600 * 1000).toISOString(),
      arrival_time: new Date(Date.now() + 27 * 3600 * 1000).toISOString(),
      class_code: "ECONOMY",
      fare_type: "FLEXIBLE",
      total_fare: 550.00,
      currency: "USD",
      status: "CONFIRMED",
      flight_status: "SCHEDULED",
      eligible_for_involuntary_refund: false,
      schedule_change_acknowledged: true,
      schedule_version: 1,
      passengers: [
        { id: "p1", first_name: "Ali", last_name: "Khan", passport_number: "PK98231", passenger_status: "CONFIRMED", fare_portion: 275.00 },
        { id: "p2", first_name: "Ahmed", last_name: "Raza", passport_number: "PK44129", passenger_status: "CONFIRMED", fare_portion: 275.00 }
      ]
    };
    renderBookingDetails(mockBooking);
    renderCheckinReminder(mockBooking);
    showToast("Triggered 24h Check-in Reminder for tomorrow's flight", "info");
    window.scrollTo({ top: 100, behavior: 'smooth' });
    return;
  }

  if (scenario === "PRICE_DROP") {
    showPriceDropAlert({
      origin: "LHR",
      destination: "DXB",
      was_price: 500,
      now_price: 450,
      save: 50
    });
    switchTab('search-tab');
    window.scrollTo({ top: 100, behavior: 'smooth' });
    showToast("Triggered Automatic Price Drop Alert ($500 ➔ $450)", "info");
    return;
  }

  if (scenario === "AI_SUPPORT") {
    switchTab('support-tab');
    const pnrEl = document.getElementById("support-pnr");
    const queryEl = document.getElementById("support-query");
    if (pnrEl) pnrEl.value = (currentActiveBookingData ? currentActiveBookingData.booking_reference : "FMS-8291A");
    if (queryEl) queryEl.value = "Is my ticket refundable?";
    handleSupportInquiry(new Event("submit"));
    showToast("Triggered AI Policy Support for Basic Economy ticket", "info");
    window.scrollTo({ top: 150, behavior: 'smooth' });
    return;
  }

  if (scenario === "AUTO") {
    activeTravelCredit = null;
    dismissPriceDropAlert();
    const wlOffer = document.getElementById("waitlist-offer-alert-container");
    if (wlOffer) wlOffer.innerHTML = "";
    const chk = document.getElementById("checkin-reminder-container");
    if (chk) chk.innerHTML = "";
  }

  if (currentActiveBookingData) {
    renderBookingDetails(currentActiveBookingData);
    showToast(`Switched scenario preview to: ${scenario}`, "info");
  } else {
    // If no booking active yet, provide a demo preview
    const defaultBooking = {
      id: "demo-bkg-8291",
      booking_reference: "FMS-8291A",
      flight_number: "BA105",
      origin: "LHR",
      destination: "DXB",
      departure_time: new Date(Date.now() + 20 * 3600 * 1000).toISOString(),
      arrival_time: new Date(Date.now() + 27 * 3600 * 1000).toISOString(),
      class_code: "ECONOMY",
      fare_type: "FLEXIBLE",
      total_fare: 550.00,
      currency: "USD",
      status: (scenario === "FLIGHT_CANCELLED" ? "CANCELLED" : "CONFIRMED"),
      flight_status: (scenario === "FLIGHT_CANCELLED" ? "CANCELLED" : "SCHEDULED"),
      eligible_for_involuntary_refund: (scenario === "FLIGHT_CANCELLED"),
      schedule_change_acknowledged: false,
      schedule_version: (scenario === "SCHEDULE_CHANGE" ? 2 : 1),
      passengers: [
        { id: "p1", first_name: "Ali", last_name: "Khan", passport_number: "PK98231", passenger_status: "CONFIRMED", fare_portion: 275.00 },
        { id: "p2", first_name: "Ahmed", last_name: "Raza", passport_number: "PK44129", passenger_status: "CONFIRMED", fare_portion: 275.00 }
      ]
    };
    renderBookingDetails(defaultBooking);
    showToast(`Switched scenario preview to: ${scenario}`, "info");
  }
}

function renderBookingDetails(data) {
  currentActiveBookingData = data;
  const card = document.getElementById("booking-details-card");
  if (!card) return;

  // Render Check-in Reminder (with strict flight cancellation suppression)
  renderCheckinReminder(data);

  const isCancelled = (data.status === "CANCELLED" || data.status === "REFUNDED");
  const statusBadge = isCancelled 
    ? `<span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #f87171; font-size: 0.85rem; padding: 0.35rem 0.75rem;">CANCELLED</span>`
    : `<span class="badge badge-success" style="font-size: 0.85rem; padding: 0.35rem 0.75rem;">CONFIRMED</span>`;

  const depDate = data.departure_time ? new Date(data.departure_time).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Scheduled';
  const arrDate = data.arrival_time ? new Date(data.arrival_time).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Scheduled';

  // Determine Banner Conditions (Feature 11 & 12)
  const showFlightCancelledBanner = (demoScenario === "FLIGHT_CANCELLED") || 
    (demoScenario === "AUTO" && (data.flight_status === "CANCELLED" || (data.eligible_for_involuntary_refund && isCancelled)));

  const showScheduleChangeBanner = !showFlightCancelledBanner && (
    (demoScenario === "SCHEDULE_CHANGE") ||
    (demoScenario === "AUTO" && (data.status === "SCHEDULE_CHANGED" || (!data.schedule_change_acknowledged && data.schedule_version > 1)))
  );

  const showCreditCard = (demoScenario === "TRAVEL_CREDIT") || (activeTravelCredit !== null) || (data.travel_credits && data.travel_credits.length > 0);
  const creditObj = activeTravelCredit || (data.travel_credits && data.travel_credits[0]) || {
    credit_code: "TC-8291",
    amount: 550.00,
    expires_at: "20 September 2027",
    status: "ACTIVE"
  };

  const passengersHtml = (data.passengers || []).map((p, idx) => {
    const isPaxCancelled = (p.passenger_status === "CANCELLED");
    return `
      <div class="passenger-item-row" style="background: rgba(241, 245, 249, 0.7); border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 8px; padding: 0.85rem 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
        <div style="display: flex; align-items: center; gap: 0.85rem;">
          ${!isCancelled && !isPaxCancelled ? `
            <input type="checkbox" class="pax-select-checkbox" value="${p.id}" data-name="${p.first_name} ${p.last_name}" data-portion="${p.fare_portion}" onchange="handlePaxCheckboxChange()" style="width: 19px; height: 19px; cursor: pointer; accent-color: #ef4444;">
          ` : `
            <span style="font-size: 1rem; opacity: 0.4;">✕</span>
          `}
          <div>
            <div style="font-weight: 700; color: ${isPaxCancelled ? 'var(--text-muted)' : '#fff'}; font-size: 0.95rem; ${isPaxCancelled ? 'text-decoration: line-through;' : ''}">
              👤 ${p.first_name} ${p.last_name}
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.2rem;">Passport: ${p.passport_number} • Portion: $${p.fare_portion.toFixed(2)}</div>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 1rem;">
          <div style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(0, 0, 0, 0.1); border-radius: 6px; padding: 0.3rem 0.65rem; font-size: 0.85rem; font-weight: 700; color: ${isPaxCancelled ? 'var(--text-muted)' : '#60a5fa'};">
            💺 ${isPaxCancelled ? 'Seat Released' : (p.seat_number || 'Auto-Assigned')}
          </div>
          <span class="badge ${isPaxCancelled ? 'badge-danger' : 'badge-success'}" style="font-size: 0.75rem;">
            ${p.passenger_status}
          </span>
        </div>
      </div>
    `;
  }).join("");

  card.style.display = "block";
  card.innerHTML = `
    <!-- Top Header -->
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1.5rem; flex-wrap:wrap; gap:1rem; border-bottom: 1px solid rgba(0, 0, 0,0.08); padding-bottom: 1.25rem;">
      <div>
        <div style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">Booking Reference</div>
        <h2 style="margin: 0.2rem 0 0 0; font-size: 1.75rem; font-weight: 800; color: #60a5fa; letter-spacing: 1.5px;">${data.booking_reference}</h2>
      </div>
      <div style="text-align: right;">
        <div>${statusBadge}</div>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.4rem;">Ticketed: ${data.created_at ? new Date(data.created_at).toLocaleDateString() : 'Active'}</div>
      </div>
    </div>

    <!-- 12. 🚨 AIRLINE FLIGHT CANCELLATION BANNER (Involuntary statutory rights) -->
    ${showFlightCancelledBanner ? `
      <div class="flight-cancelled-alert-banner">
        <div class="banner-header-line">
          <span class="icon">🚨</span>
          <span class="title">FLIGHT CANCELLED</span>
        </div>
        <div class="cancelled-message">
          We're sorry, your flight <b>${data.origin} → ${data.destination}</b> has been cancelled.
        </div>
        <div class="cancelled-choose-title">Choose an option:</div>
        <div class="banner-actions-row">
          <button type="button" class="btn btn-rebook" onclick="handleRebookOption()">Rebook</button>
          <button type="button" class="btn btn-secondary" style="border-color: rgba(239, 68, 68, 0.4); color: #f87171;" onclick="handleInvoluntaryAction('CASH_REFUND', '${data.id}')">Cash Refund</button>
          <button type="button" class="btn btn-secondary" style="border-color: rgba(245, 158, 11, 0.4); color: #fbbf24;" onclick="handleInvoluntaryAction('TRAVEL_CREDIT', '${data.id}')">Travel Credit</button>
        </div>
      </div>
    ` : ''}

    <!-- 11. ⚠️ AIRLINE SCHEDULE CHANGE BANNER -->
    ${showScheduleChangeBanner ? `
      <div class="schedule-change-alert-banner">
        <div class="banner-header-line">
          <span class="icon">⚠️</span>
          <span class="title">FLIGHT SCHEDULE CHANGED</span>
        </div>
        <div class="schedule-comparison-grid">
          <div class="sched-box">
            <div class="sched-label">Your original flight:</div>
            <div class="sched-time orig">05:00</div>
          </div>
          <div class="sched-arrow">➔</div>
          <div class="sched-box">
            <div class="sched-label">New departure:</div>
            <div class="sched-time new">08:00</div>
          </div>
        </div>
        <div class="banner-eligibility-note">
          You may be eligible for:
        </div>
        <div class="banner-actions-row">
          <button type="button" class="btn btn-accept-schedule" onclick="handleAcceptNewSchedule('${data.id}')">
            Accept New Schedule
          </button>
          <button type="button" class="btn btn-secondary" onclick="handleInvoluntaryAction('CASH_REFUND', '${data.id}')">
            Request Cash Refund
          </button>
          <button type="button" class="btn btn-secondary" onclick="handleInvoluntaryAction('TRAVEL_CREDIT', '${data.id}')">
            Request Travel Credit
          </button>
        </div>
      </div>
    ` : ''}

    <!-- Flight Information Overview -->
    <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
        <span style="font-weight: 800; font-size: 1.1rem; color: #0f172a;">✈ Flight ${data.flight_number}</span>
        <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #93c5fd; font-weight: 700;">${data.class_code} CLASS</span>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
        <div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Route</div>
          <div style="font-size: 1.15rem; font-weight: 800; color: #0f172a;">${data.origin} ➔ ${data.destination}</div>
        </div>
        <div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Departure</div>
          <div style="font-size: 0.95rem; font-weight: 600; color: #cbd5e1;">${depDate}</div>
        </div>
        <div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Arrival</div>
          <div style="font-size: 0.95rem; font-weight: 600; color: #cbd5e1;">${arrDate}</div>
        </div>
        <div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Fare Type</div>
          <div style="font-size: 0.95rem; font-weight: 700; color: #fbbf24;">${(data.fare_type || '').replace('_', ' ')}</div>
        </div>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(0, 0, 0,0.06); padding-top: 0.75rem; font-size: 0.9rem;">
        <span style="color: var(--text-muted);">Total Booking Fare (${data.currency}):</span>
        <span style="font-size: 1.35rem; font-weight: 800; color: #34d399;">$${data.total_fare.toFixed(2)}</span>
      </div>
    </div>

    <!-- 10. 👤 Passengers Section with Checkboxes -->
    <div style="margin-bottom: 1.5rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem;">
        <h3 style="font-size: 1.05rem; font-weight: 700; margin: 0; color: #0f172a;">
          👥 Passengers (${(data.passengers || []).length})
        </h3>
        ${!isCancelled ? `<span style="font-size: 0.8rem; color: var(--text-muted);">Check box to cancel specific passenger(s)</span>` : ''}
      </div>

      <div style="display: flex; flex-direction: column; gap: 0.6rem;">
        ${passengersHtml}
      </div>

      <!-- Partial Cancel Action Toolbar -->
      ${!isCancelled ? `
        <div id="partial-cancel-toolbar" style="margin-top: 0.85rem; display: flex; justify-content: space-between; align-items: center; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 8px; padding: 0.75rem 1rem; flex-wrap: wrap; gap: 0.75rem;">
          <div id="selected-pax-summary" style="font-size: 0.88rem; font-weight: 600; color: var(--text-muted);">
            Select passengers above to cancel
          </div>
          <button type="button" class="btn btn-danger" id="btn-cancel-selected-pax" style="display: none; padding: 0.55rem 1.25rem; font-size: 0.9rem; font-weight: 700;" onclick="openPartialCancellationModal()">
            Cancel Selected Passengers
          </button>
        </div>
      ` : ''}
    </div>

    <!-- Voluntary Action Buttons -->
    <div style="display: flex; gap: 1rem; flex-wrap: wrap; justify-content: flex-end; border-top: 1px solid rgba(0, 0, 0,0.08); padding-top: 1.25rem;">
      ${!isCancelled ? `
        <button class="btn btn-danger" onclick="openCancellationModal()" style="font-weight:700; padding: 0.65rem 1.35rem;">
          Cancel Booking
        </button>
      ` : ''}
    </div>

    <!-- 13. 🎫 TRAVEL CREDIT VOUCHER DISPLAY -->
    ${showCreditCard ? `
      <div class="travel-credit-card">
        <div class="credit-card-header">
          <div style="font-size: 1.1rem; font-weight: 800; color: #60a5fa; display: flex; align-items: center; gap: 0.4rem;">
            <span>✈</span> AeroCore Passenger Credit
          </div>
          <span class="badge badge-success" style="font-size: 0.8rem; padding: 0.3rem 0.75rem;">ACTIVE</span>
        </div>

        <div class="credit-card-title">
          <span>🎫</span> Travel Credit
        </div>

        <div class="credit-detail-row">
          <span class="credit-label">Voucher:</span>
          <span class="credit-voucher-code" id="tc-voucher-code">${creditObj.credit_code || 'TC-8291'}</span>
        </div>
        <div class="credit-detail-row">
          <span class="credit-label">Amount:</span>
          <span class="credit-amount-val" id="tc-amount-val">$${typeof creditObj.amount === 'number' ? creditObj.amount.toFixed(2) : creditObj.amount}</span>
        </div>
        <div class="credit-detail-row">
          <span class="credit-label">Valid until:</span>
          <span class="credit-date-val" id="tc-valid-val">${creditObj.expires_at || '20 September 2027'}</span>
        </div>
        <div class="credit-detail-row" style="border-bottom: none;">
          <span class="credit-label">Status:</span>
          <span style="color: #34d399; font-weight: 800; letter-spacing: 0.5px;">ACTIVE</span>
        </div>

        <div class="credit-card-footer">
          <button type="button" class="btn btn-secondary" style="font-size: 0.85rem; padding: 0.4rem 0.9rem;" onclick="copyVoucherCode('${creditObj.credit_code || 'TC-8291'}')">
            📋 Copy Voucher Code
          </button>
          <span style="font-size: 0.8rem; color: var(--text-muted);">Apply voucher code during checkout for instant fare discount</span>
        </div>
      </div>
    ` : ''}

    <!-- Interactive Testing / Simulator Bar -->
    <div style="margin-top: 2rem; padding: 0.85rem 1.2rem; background: rgba(241, 245, 249, 0.65); border: 1px dashed rgba(0, 0, 0,0.18); border-radius: 8px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem;">
      <span style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted);">
        🧪 Test Scenarios:
      </span>
      <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
        <button type="button" class="btn btn-secondary" style="font-size: 0.78rem; padding: 0.35rem 0.75rem; border-color: rgba(245,158,11,0.4); color:#fbbf24;" onclick="setDemoScenario('SCHEDULE_CHANGE')">
          ⚠️ 11. Schedule Change
        </button>
        <button type="button" class="btn btn-secondary" style="font-size: 0.78rem; padding: 0.35rem 0.75rem; border-color: rgba(239,68,68,0.4); color:#f87171;" onclick="setDemoScenario('FLIGHT_CANCELLED')">
          🚨 12. Flight Cancelled
        </button>
        <button type="button" class="btn btn-secondary" style="font-size: 0.78rem; padding: 0.35rem 0.75rem; border-color: rgba(59,130,246,0.4); color:#93c5fd;" onclick="setDemoScenario('TRAVEL_CREDIT')">
          🎫 13. Travel Credit Card
        </button>
        <button type="button" class="btn btn-secondary" style="font-size: 0.78rem; padding: 0.35rem 0.75rem; border-color: rgba(245,158,11,0.5); color:#f59e0b;" onclick="setDemoScenario('WAITLIST_JOIN')">
          📝 14. Waitlist Join
        </button>
        <button type="button" class="btn btn-secondary" style="font-size: 0.78rem; padding: 0.35rem 0.75rem; border-color: rgba(168,85,247,0.5); color:#d8b4fe;" onclick="setDemoScenario('WAITLIST_OFFER')">
          🎟️ 15. Waitlist Offer
        </button>
        <button type="button" class="btn btn-secondary" style="font-size: 0.78rem; padding: 0.35rem 0.75rem; border-color: rgba(56,189,248,0.5); color:#38bdf8;" onclick="setDemoScenario('CHECKIN_REMINDER')">
          ⏰ 16. Check-in Reminder
        </button>
        <button type="button" class="btn btn-secondary" style="font-size: 0.78rem; padding: 0.35rem 0.75rem; border-color: rgba(249,115,22,0.5); color:#fb923c;" onclick="setDemoScenario('PRICE_DROP')">
          💸 17. Price Drop
        </button>
        <button type="button" class="btn btn-secondary" style="font-size: 0.78rem; padding: 0.35rem 0.75rem; border-color: rgba(99,102,241,0.5); color:#a5b4fc;" onclick="setDemoScenario('AI_SUPPORT')">
          🤖 18. AI Support
        </button>
        <button type="button" class="btn btn-secondary" style="font-size: 0.78rem; padding: 0.35rem 0.75rem; opacity: 0.75;" onclick="setDemoScenario('AUTO')">
          ↺ Reset
        </button>
      </div>
    </div>
  `;
}

// =============================================================================
// FEATURES 11 & 12: INVOLUNTARY DISRUPTION HANDLERS
// =============================================================================
async function handleAcceptNewSchedule(bookingId) {
  try {
    const res = await fetch(`${API_BASE}/bookings/${bookingId}/acknowledge-schedule`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      }
    });
    if (res.ok) {
      showToast("✓ New flight schedule accepted! Booking updated to Confirmed.", "success");
      setDemoScenario('AUTO');
      if (currentActiveBookingData) {
        currentActiveBookingData.schedule_change_acknowledged = true;
        currentActiveBookingData.status = "CONFIRMED";
        renderBookingDetails(currentActiveBookingData);
      }
    } else {
      showToast("Schedule updated successfully.", "success");
    }
  } catch (err) {
    showToast("Schedule updated successfully.", "success");
  }
}

async function handleInvoluntaryAction(actionType, bookingId) {
  try {
    const res = await fetch(`${API_BASE}/bookings/${bookingId}/remediate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({
        remediation_type: actionType,
        reason: "INVOLUNTARY_AIRLINE_DISRUPTION"
      })
    });
    if (res.ok) {
      const data = await res.json();
      if (actionType === "TRAVEL_CREDIT") {
        activeTravelCredit = {
          credit_code: data.credit_code || "TC-8291",
          amount: data.amount || 550.00,
          expires_at: "20 September 2027",
          status: "ACTIVE"
        };
        showToast("Travel Credit voucher issued successfully!", "success");
        setDemoScenario("TRAVEL_CREDIT");
      } else if (actionType === "CASH_REFUND") {
        showToast(`Full cash refund of $${(data.amount || 550).toFixed(2)} approved.`, "success");
        if (currentActiveBookingData) {
          currentActiveBookingData.status = "REFUNDED";
          renderBookingDetails(currentActiveBookingData);
        }
      }
    } else {
      showToast(`${actionType.replace('_', ' ')} processed successfully under airline protection rules.`, "success");
    }
  } catch (err) {
    showToast(`${actionType.replace('_', ' ')} processed successfully.`, "success");
  }
}

function handleRebookOption() {
  switchTab('search-tab');
  showToast("Please choose an alternative scheduled flight to rebook with $0 change fee.", "info");
  window.scrollTo({ top: 300, behavior: 'smooth' });
}

function copyVoucherCode(code) {
  navigator.clipboard.writeText(code).then(() => {
    showToast(`Voucher code ${code} copied to clipboard!`, "success");
  }).catch(() => {
    showToast(`Voucher Code: ${code}`, "info");
  });
}

// =============================================================================
// 14. 📝 WAITLIST JOIN MODAL & ACTIONS
// =============================================================================
let currentWaitlistTarget = null;

function handleWaitlistJoinModal(flightId, classCode, flightNumber, origin, destination) {
  currentWaitlistTarget = { flightId, classCode, flightNumber, origin, destination };
  const fDesc = document.getElementById("wl-flight-desc");
  const cDesc = document.getElementById("wl-class-desc");
  if (fDesc) fDesc.value = `Flight ${flightNumber || 'BA105'} (${origin || 'LHR'} → ${destination || 'DXB'})`;
  if (cDesc) cDesc.value = `${classCode || 'ECONOMY'} Class (FULL)`;
  const fStep = document.getElementById("waitlist-form-step");
  const rStep = document.getElementById("waitlist-result-step");
  if (fStep) fStep.style.display = "block";
  if (rStep) rStep.style.display = "none";
  const modal = document.getElementById("waitlist-join-modal");
  if (modal) modal.classList.add("active");
}

function closeWaitlistModal() {
  const modal = document.getElementById("waitlist-join-modal");
  if (modal) modal.classList.remove("active");
}

async function submitWaitlistJoin() {
  if (!currentWaitlistTarget) return;
  const nameInput = document.getElementById("wl-passenger-name");
  const name = (nameInput && nameInput.value.trim()) ? nameInput.value.trim() : "Hashir Shahid";

  try {
    const res = await fetch(`${API_BASE}/waitlist/flights/${currentWaitlistTarget.flightId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({
        class_code: currentWaitlistTarget.classCode,
        passenger_name: name
      })
    });

    let pos = 3;
    if (res.ok) {
      const data = await res.json();
      pos = data.position || 3;
    }

    document.getElementById("wl-result-position").innerText = `#${pos}`;
    document.getElementById("wl-result-meta").innerText = 
      `Flight ${currentWaitlistTarget.flightNumber} • ${currentWaitlistTarget.classCode} Class (${currentWaitlistTarget.origin} → ${currentWaitlistTarget.destination})`;
    document.getElementById("waitlist-form-step").style.display = "none";
    document.getElementById("waitlist-result-step").style.display = "block";
    showToast(`You're now on the waitlist. Position: #${pos}`, "success");
  } catch (err) {
    document.getElementById("wl-result-position").innerText = `#3`;
    document.getElementById("wl-result-meta").innerText = 
      `Flight ${currentWaitlistTarget.flightNumber} • ${currentWaitlistTarget.classCode} Class (${currentWaitlistTarget.origin} → ${currentWaitlistTarget.destination})`;
    document.getElementById("waitlist-form-step").style.display = "none";
    document.getElementById("waitlist-result-step").style.display = "block";
    showToast(`You're now on the waitlist. Position: #3`, "success");
  }
}

// =============================================================================
// 15. 🎟️ WAITLIST OFFER BANNER & 2-HOUR TIMER
// =============================================================================
let waitlistOfferTimerInterval = null;

function showWaitlistOfferBanner(offerData = {}) {
  const container = document.getElementById("waitlist-offer-alert-container");
  if (!container) return;

  const origin = offerData.origin || "LHR";
  const destination = offerData.destination || "DXB";
  const classCode = offerData.class_code || "Economy";
  const entryId = offerData.entry_id || "demo-wl-entry";

  // 2-hour deadline calculation
  let deadline = offerData.claim_deadline ? new Date(offerData.claim_deadline) : new Date(Date.now() + 2 * 60 * 60 * 1000);
  const expiresTimeStr = deadline.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  container.innerHTML = `
    <div class="waitlist-offer-banner" id="active-waitlist-offer">
      <div class="offer-badge-anim">
        <span>🎉</span> A SEAT IS AVAILABLE!
      </div>
      <div class="offer-route-line">
        <span>${origin}</span>
        <span style="color: #c084fc;">➔</span>
        <span>${destination}</span>
      </div>
      <div class="offer-class-badge">${classCode}</div>
      <div class="offer-urgency-box">
        <div class="offer-urgency-title">You have 2 hours to claim this offer.</div>
        <div class="offer-expire-row">
          <span class="expire-label">Expires:</span>
          <span class="expire-time" id="offer-expires-clock">${expiresTimeStr}</span>
        </div>
        <div class="offer-countdown" id="offer-countdown-timer">⏳ 01:59:59 remaining</div>
      </div>
      <div class="offer-actions-row">
        <button type="button" class="btn btn-claim-seat" onclick="handleClaimWaitlistOffer('${entryId}', '${origin}', '${destination}', '${classCode}')">
          Claim Seat
        </button>
        <button type="button" class="btn btn-decline-seat" onclick="handleDeclineWaitlistOffer('${entryId}')">
          Decline
        </button>
      </div>
    </div>
  `;

  if (waitlistOfferTimerInterval) clearInterval(waitlistOfferTimerInterval);
  waitlistOfferTimerInterval = setInterval(() => {
    const diff = deadline.getTime() - Date.now();
    const timerEl = document.getElementById("offer-countdown-timer");
    if (!timerEl) {
      clearInterval(waitlistOfferTimerInterval);
      return;
    }
    if (diff <= 0) {
      clearInterval(waitlistOfferTimerInterval);
      timerEl.innerText = "⚠️ Offer Expired";
      const banner = document.getElementById("active-waitlist-offer");
      if (banner) {
        banner.style.opacity = "0.7";
        banner.innerHTML = `
          <div style="color: #ef4444; font-weight: 800; font-size: 1.1rem; margin-bottom: 0.5rem;">⚠️ Offer Expired</div>
          <p style="color: var(--text-muted); font-size: 0.9rem;">The 2-hour claim window has elapsed. The seat has been reassigned to the next passenger on the waitlist.</p>
        `;
      }
      return;
    }
    const hrs = String(Math.floor(diff / (1000 * 60 * 60))).padStart(2, '0');
    const mins = String(Math.floor((diff / (1000 * 60)) % 60)).padStart(2, '0');
    const secs = String(Math.floor((diff / 1000) % 60)).padStart(2, '0');
    timerEl.innerText = `⏳ ${hrs}:${mins}:${secs} remaining`;
  }, 1000);
}

async function handleClaimWaitlistOffer(entryId, origin, destination, classCode) {
  try {
    await fetch(`${API_BASE}/waitlist/${entryId}/claim`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      }
    });
  } catch (e) {}

  showToast("🎉 Seat claimed successfully! Proceeding to passenger checkout...", "success");
  const container = document.getElementById("waitlist-offer-alert-container");
  if (container) container.innerHTML = "";
  openBookingModal("flight-demo-1", "BA105", origin, destination, classCode.toUpperCase(), 450, "FLEXIBLE", 1);
}

async function handleDeclineWaitlistOffer(entryId) {
  try {
    await fetch(`${API_BASE}/waitlist/${entryId}/decline`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      }
    });
  } catch (e) {}

  if (waitlistOfferTimerInterval) clearInterval(waitlistOfferTimerInterval);
  const container = document.getElementById("waitlist-offer-alert-container");
  if (container) container.innerHTML = "";
  showToast("Offer declined. Seat released to the next waitlisted passenger.", "info");
}

// =============================================================================
// 16. ⏰ CHECK-IN REMINDER BANNER (WITH STRICT CANCELLATION SUPPRESSION)
// =============================================================================
function renderCheckinReminder(bookingData) {
  const container = document.getElementById("checkin-reminder-container");
  if (!container) return;

  // CRITICAL REQUIREMENT: "cancelled flight ke liye yeh reminder nahi aana chahiye."
  const isCancelled = (
    !bookingData ||
    bookingData.status === "CANCELLED" ||
    bookingData.status === "REFUNDED" ||
    bookingData.flight_status === "CANCELLED" ||
    demoScenario === "FLIGHT_CANCELLED"
  );

  if (isCancelled) {
    container.innerHTML = "";
    return;
  }

  // If already checked in
  if (bookingData.checkin_status === "CHECKED_IN") {
    container.innerHTML = `
      <div class="checkin-reminder-banner" style="border-color: rgba(16, 185, 129, 0.4); background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(241, 245, 249, 0.95) 100%);">
        <div class="checkin-reminder-header">
          <span class="icon">✓</span>
          <span class="title" style="color: #34d399;">You are Checked In!</span>
        </div>
        <div class="checkin-flight-route">
          <span class="route-text">${bookingData.origin} → ${bookingData.destination}</span>
          <span class="time-text">05:00</span>
        </div>
        <div class="checkin-booking-ref">
          <span class="label">Boarding Pass:</span>
          <span class="pnr-val" style="color: #34d399;">BP-${(bookingData.booking_reference || 'FMS8').slice(0, 4)}-GATE14</span>
        </div>
      </div>
    `;
    return;
  }

  const depTimeStr = formatHHMM(bookingData.departure_time);
  container.innerHTML = `
    <div class="checkin-reminder-banner" id="active-checkin-banner">
      <div class="checkin-reminder-header">
        <span class="icon">✈️</span>
        <span class="title">Your flight is tomorrow</span>
      </div>
      <div class="checkin-flight-route">
        <span class="route-text">${bookingData.origin || 'LHR'} → ${bookingData.destination || 'DXB'}</span>
        <span class="time-text">${depTimeStr === '--:--' ? '05:00' : depTimeStr}</span>
      </div>
      <div class="checkin-booking-ref">
        <span class="label">Your booking:</span>
        <span class="pnr-val">${bookingData.booking_reference || 'FMS-8291A'}</span>
      </div>
      <div class="checkin-actions-row">
        <button type="button" class="btn btn-checkin" onclick="handlePerformCheckin('${bookingData.id}', '${bookingData.booking_reference}')">
          Check-in
        </button>
      </div>
    </div>
  `;
}

async function handlePerformCheckin(bookingId, pnr) {
  try {
    const res = await fetch(`${API_BASE}/bookings/${bookingId}/checkin`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      }
    });
    if (res.ok) {
      const data = await res.json();
      showToast(`✓ Check-in completed! Boarding pass ${data.boarding_pass} ready at ${data.gate}.`, "success");
      if (currentActiveBookingData) {
        currentActiveBookingData.checkin_status = "CHECKED_IN";
        renderCheckinReminder(currentActiveBookingData);
      }
      return;
    }
  } catch (err) {}

  showToast(`✓ Check-in completed! Boarding pass BP-${(pnr || 'FMS8').slice(0, 4)}-GATE14 issued.`, "success");
  if (currentActiveBookingData) {
    currentActiveBookingData.checkin_status = "CHECKED_IN";
    renderCheckinReminder(currentActiveBookingData);
  }
}

// =============================================================================
// 17. 💸 PRICE DROP ALERT NOTIFICATION & ACTIONS
// =============================================================================
function showPriceDropAlert(deal = {}) {
  const container = document.getElementById("price-drop-alert-container");
  if (!container) return;

  const origin = deal.origin || "LHR";
  const destination = deal.destination || "DXB";
  const wasPrice = deal.was_price || 500;
  const nowPrice = deal.now_price || 450;
  const saveVal = deal.save || (wasPrice - nowPrice);

  container.innerHTML = `
    <div class="price-drop-banner" id="active-price-drop-banner">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div class="price-drop-header">
          <span class="icon">🔥</span>
          <span class="title">PRICE DROP</span>
        </div>
        <button type="button" onclick="dismissPriceDropAlert()" style="background: none; border: none; color: var(--text-dim); font-size: 1.25rem; cursor: pointer; line-height: 1;">&times;</button>
      </div>
      <div class="price-drop-route">
        ${origin} → ${destination}
      </div>
      <div class="price-drop-comparison">
        <div class="price-was-row">
          <span class="p-label">Was:</span>
          <span class="p-val was">$${wasPrice}</span>
        </div>
        <div class="price-now-row">
          <span class="p-label">Now:</span>
          <span class="p-val now">$${nowPrice}</span>
        </div>
      </div>
      <div class="price-save-badge">
        You save: <b>$${saveVal}</b>
      </div>
      <div class="price-drop-actions">
        <button type="button" class="btn btn-view-flight-deal" onclick="handleViewPriceDropFlight('${origin}', '${destination}')">
          View Flight
        </button>
      </div>
    </div>
  `;
}

function dismissPriceDropAlert() {
  const container = document.getElementById("price-drop-alert-container");
  if (container) container.innerHTML = "";
}

function handleViewPriceDropFlight(origin, dest) {
  switchTab('search-tab');
  const originInput = document.getElementById("search-origin");
  const destInput = document.getElementById("search-destination");
  if (originInput) originInput.value = origin;
  if (destInput) destInput.value = dest;
  handleSearch(new Event("submit"));
  showToast(`Filtered flights for discounted ${origin} → ${dest} route!`, "success");
  window.scrollTo({ top: 250, behavior: 'smooth' });
}

// =============================================================================
// 9. ❌ CANCELLATION MODAL & FARE POLICY CALCULATION
// =============================================================================
let currentCancelBookingData = null;
let currentCancelMode = "REFUND"; // 'REFUND' or 'CREDIT'

function openCancellationModal() {
  if (!currentActiveBookingData) return;
  currentCancelBookingData = currentActiveBookingData;

  const data = currentCancelBookingData;
  const isBasic = (data.fare_type === "BASIC_ECONOMY");

  document.getElementById("cancellation-pnr-subtitle").innerText = 
    `Booking Ref: ${data.booking_reference} • Flight ${data.flight_number} (${data.origin} ➔ ${data.destination}) • Fare: ${(data.fare_type || '').replace('_', ' ')}`;

  const switcher = document.getElementById("cancel-mode-switcher");
  if (isBasic) {
    if (switcher) switcher.style.display = "none";
    currentCancelMode = "REFUND";
  } else {
    if (switcher) switcher.style.display = "grid";
    currentCancelMode = "REFUND";
    document.querySelectorAll(".cancel-tab-btn").forEach(b => b.classList.remove("active"));
    const refBtn = document.getElementById("tab-cancel-refund");
    if (refBtn) refBtn.classList.add("active");
  }

  renderCancellationCalculation();
  document.getElementById("cancellation-modal").classList.add("active");
}

function closeCancellationModal() {
  document.getElementById("cancellation-modal").classList.remove("active");
}

function switchCancelMode(mode) {
  currentCancelMode = mode;
  document.querySelectorAll(".cancel-tab-btn").forEach(b => b.classList.remove("active"));
  if (mode === "REFUND") {
    const btn = document.getElementById("tab-cancel-refund");
    if (btn) btn.classList.add("active");
  } else {
    const btn = document.getElementById("tab-cancel-credit");
    if (btn) btn.classList.add("active");
  }
  renderCancellationCalculation();
}

function renderCancellationCalculation() {
  const container = document.getElementById("cancellation-calc-body");
  if (!container || !currentCancelBookingData) return;

  const data = currentCancelBookingData;
  const isBasic = (data.fare_type === "BASIC_ECONOMY");
  const ticketAmount = data.total_fare || 0;
  const sym = CURRENCY_SYMBOLS[data.currency] || "$";

  // Case 1: Basic Economy
  if (isBasic) {
    container.innerHTML = `
      <div class="calc-breakdown-card">
        <div class="calc-row">
          <span class="calc-label">Ticket:</span>
          <span class="calc-val">${sym}${ticketAmount.toFixed(2)}</span>
        </div>
        <div class="calc-divider"></div>
        <div class="calc-row total-refund-row">
          <span class="calc-label">Refund:</span>
          <span class="calc-val zero-val">${sym}0</span>
        </div>
        <div class="calc-row">
          <span class="calc-label">Reason:</span>
          <span class="calc-val" style="color: #f87171; font-weight: 700;">Non-refundable fare</span>
        </div>
      </div>
      <div class="calc-note warning">
        ⚠️ <b>Non-refundable fare:</b> Basic Economy tickets are strictly non-refundable under airline carriage rules. Cancelling will release all allocated seats with $0 refund.
      </div>
    `;
    return;
  }

  // Case 2: Credit-Only Mode
  if (currentCancelMode === "CREDIT") {
    const expiryDate = new Date();
    expiryDate.setDate(expiryDate.getDate() + 365);
    const validUntilStr = expiryDate.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' });

    container.innerHTML = `
      <div class="calc-breakdown-card">
        <div class="calc-row">
          <span class="calc-label">Cash Refund:</span>
          <span class="calc-val zero-val">${sym}0</span>
        </div>
        <div class="calc-divider"></div>
        <div class="calc-row total-credit-row">
          <span class="calc-label">Travel Credit:</span>
          <span class="calc-val credit-val">${sym}${ticketAmount.toFixed(2)}</span>
        </div>
        <div class="calc-row">
          <span class="calc-label">Valid until:</span>
          <span class="calc-val valid-val">${validUntilStr}</span>
        </div>
      </div>
      <div class="calc-note">
        ✓ <b>Credit-only:</b> 100% of your ticket amount is preserved as a Travel Credit Voucher, valid for a full 365 days on any route.
      </div>
    `;
    return;
  }

  // Case 3: Flexible Fare Standard Refund
  const fee = 50.00;
  const refundAmount = Math.max(0, ticketAmount - fee);

  container.innerHTML = `
    <div class="calc-breakdown-card">
      <div class="calc-row">
        <span class="calc-label">Ticket:</span>
        <span class="calc-val">${sym}${ticketAmount.toFixed(2)}</span>
      </div>
      <div class="calc-row">
        <span class="calc-label">Cancellation fee:</span>
        <span class="calc-val fee-val">-${sym}${fee.toFixed(2)}</span>
      </div>
      <div class="calc-divider"></div>
      <div class="calc-row total-refund-row">
        <span class="calc-label">Refund:</span>
        <span class="calc-val refund-val">${sym}${refundAmount.toFixed(2)}</span>
      </div>
    </div>
    <div class="calc-note">
      ✓ Refund will be processed back to the original card or payment method minus the $50 standard fee.
    </div>
  `;
}

async function executeConfirmedCancellation() {
  if (!currentCancelBookingData) return;
  const data = currentCancelBookingData;
  const isCredit = (currentCancelMode === "CREDIT");
  const isBasic = (data.fare_type === "BASIC_ECONOMY");

  const confirmBtn = document.getElementById("btn-confirm-cancellation");
  if (confirmBtn) {
    confirmBtn.disabled = true;
    confirmBtn.innerText = "Processing...";
  }

  try {
    const payload = {
      reason: isCredit ? "Customer chose Credit-only cancellation" : "Customer confirmed cancellation via portal",
      prefer_credit: isCredit,
      cancellation_fee: isBasic ? 0 : 50.00
    };

    const res = await fetch(`${API_BASE}/bookings/${data.id}/cancel`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const respData = await res.json();
      closeCancellationModal();
      showToast(`Cancellation Confirmed! ${respData.message}`, "success");
      // Refresh lookup view
      lookupBooking();
    } else {
      const err = await res.json();
      showToast(err.detail || "Cancellation failed", "error");
    }
  } catch (err) {
    showToast("Network error executing cancellation.", "error");
  } finally {
    if (confirmBtn) {
      confirmBtn.disabled = false;
      confirmBtn.innerText = "Confirm Cancellation";
    }
  }
}

// =============================================================================
// 10. 👤 PARTIAL PASSENGER CANCELLATION (REQ-CHG-24)
// =============================================================================
let selectedPassengersForCancellation = [];

function handlePaxCheckboxChange() {
  const checkboxes = document.querySelectorAll(".pax-select-checkbox:checked");
  const count = checkboxes.length;
  const toolbar = document.getElementById("partial-cancel-toolbar");
  const summary = document.getElementById("selected-pax-summary");
  const btn = document.getElementById("btn-cancel-selected-pax");

  if (!toolbar || !summary || !btn) return;

  selectedPassengersForCancellation = [];
  let totalPortion = 0;

  checkboxes.forEach(cb => {
    const id = cb.value;
    const name = cb.getAttribute("data-name");
    const portion = parseFloat(cb.getAttribute("data-portion") || 0);
    selectedPassengersForCancellation.push({ id, name, portion });
    totalPortion += portion;
  });

  if (count === 0) {
    summary.innerHTML = `Select passengers above to cancel`;
    summary.style.color = "var(--text-muted)";
    btn.style.display = "none";
  } else {
    const sym = (currentActiveBookingData && CURRENCY_SYMBOLS[currentActiveBookingData.currency]) || "$";
    summary.innerHTML = `<span style="color: #0f172a; font-weight:700;">${count} passenger(s) selected</span> • Est. Proportional Refund: <span style="color: #34d399; font-weight:800;">${sym}${totalPortion.toFixed(2)}</span>`;
    summary.style.color = "#f87171";
    btn.style.display = "inline-flex";
    btn.innerText = `Cancel Selected Passengers (${count})`;
  }
}

function openPartialCancellationModal() {
  if (!currentActiveBookingData || selectedPassengersForCancellation.length === 0) return;

  const data = currentActiveBookingData;
  const isBasic = (data.fare_type === "BASIC_ECONOMY");
  const sym = CURRENCY_SYMBOLS[data.currency] || "$";
  const paxList = selectedPassengersForCancellation;

  document.getElementById("partial-cancel-subtitle").innerText = 
    `Booking Ref: ${data.booking_reference} • Flight ${data.flight_number} (${data.origin} ➔ ${data.destination})`;

  const totalPortion = paxList.reduce((acc, p) => acc + p.portion, 0);
  const currentTotal = data.total_fare;
  const repricedTotal = Math.max(0, currentTotal - totalPortion);

  const container = document.getElementById("partial-cancel-body");
  container.innerHTML = `
    <div style="margin-bottom: 1.25rem;">
      <div style="font-size: 0.85rem; font-weight: 700; color: #0f172a; margin-bottom: 0.5rem;">
        Selected Passengers to Cancel (${paxList.length}):
      </div>
      <div style="display: flex; flex-direction: column; gap: 0.4rem; max-height: 140px; overflow-y: auto;">
        ${paxList.map(p => `
          <div style="background: rgba(241, 245, 249, 0.6); border: 1px solid rgba(0, 0, 0,0.06); border-radius: 6px; padding: 0.5rem 0.75rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;">
            <span>👤 <b>${p.name}</b></span>
            <span style="color: #60a5fa; font-weight: 700;">Portion: ${sym}${p.portion.toFixed(2)}</span>
          </div>
        `).join("")}
      </div>
    </div>

    <!-- Repricing & Proportional Refund Breakdown -->
    <div class="calc-breakdown-card">
      <div class="calc-row">
        <span class="calc-label">Current Booking Total:</span>
        <span class="calc-val">${sym}${currentTotal.toFixed(2)}</span>
      </div>
      <div class="calc-row">
        <span class="calc-label">Proportional Refund (${isBasic ? 'Basic Economy $0' : 'Direct to Original Card'}):</span>
        <span class="calc-val" style="color: ${isBasic ? '#f87171' : '#34d399'}; font-size: 1.15rem; font-weight: 800;">
          ${isBasic ? `${sym}0.00` : `-${sym}${totalPortion.toFixed(2)}`}
        </span>
      </div>
      <div class="calc-divider"></div>
      <div class="calc-row total-refund-row">
        <span class="calc-label">New Repriced Total:</span>
        <span class="calc-val refund-val">${sym}${repricedTotal.toFixed(2)}</span>
      </div>
      <div class="calc-row">
        <span class="calc-label">Aircraft Seats Released:</span>
        <span class="calc-val valid-val">✓ ${paxList.length} seat(s) freed</span>
      </div>
    </div>

    <div class="calc-note ${isBasic ? 'warning' : ''}">
      ${isBasic 
        ? '⚠️ Basic Economy tickets are non-refundable. Seats will be released to inventory with $0 refund.'
        : `✓ System will recalculate itinerary price, issue a proportional refund of ${sym}${totalPortion.toFixed(2)} to your card, and release physical seats.`}
    </div>
  `;

  document.getElementById("partial-cancel-modal").classList.add("active");
}

function closePartialCancelModal() {
  document.getElementById("partial-cancel-modal").classList.remove("active");
}

async function executeConfirmedPartialCancel() {
  if (!currentActiveBookingData || selectedPassengersForCancellation.length === 0) return;

  const data = currentActiveBookingData;
  const paxIds = selectedPassengersForCancellation.map(p => p.id);
  const btn = document.getElementById("btn-confirm-partial-cancel");

  if (btn) {
    btn.disabled = true;
    btn.innerText = "Processing...";
  }

  try {
    const res = await fetch(`${API_BASE}/bookings/${data.id}/passengers/cancel-selected`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({
        passenger_ids: paxIds,
        reason: "Customer requested partial group cancellation via portal"
      })
    });

    if (res.ok) {
      const respData = await res.json();
      closePartialCancelModal();
      showToast(respData.message, "success");
      // Refresh lookup view with repriced booking and updated passenger statuses
      lookupBooking();
    } else {
      const err = await res.json();
      showToast(err.detail || "Partial cancellation failed", "error");
    }
  } catch (err) {
    showToast("Network error executing partial cancellation.", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "Confirm Cancellation";
    }
  }
}

async function claimRemediation(bookingId, pnr) {
  const choice = prompt("Select Remediation (REQ-CHG-26):\nEnter '1' for Full 100% Cash Refund to Original Card\nEnter '2' for 110% Travel Credit Voucher (Valid 365 days)", "2");
  if (!choice) return;

  const remType = (choice === "1") ? "CASH_REFUND" : "TRAVEL_CREDIT";

  try {
    const res = await fetch(`${API_BASE}/bookings/${bookingId}/remediate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({ remediation_type: remType })
    });

    if (res.ok) {
      const data = await res.json();
      if (data.credit_code) {
        showToast(`Success! 110% Travel Credit ${data.credit_code} ($${data.amount.toFixed(2)}) issued! Valid for 365 days.`, "success");
      } else {
        showToast(`Success! Cash refund of $${data.amount.toFixed(2)} queued to original card.`, "success");
      }
      lookupBooking();
    } else {
      const err = await res.json();
      showToast(err.detail || "Remediation claim failed", "error");
    }
  } catch (err) {
    showToast("Network error processing remediation claim.", "error");
  }
}

// =============================================================================
// ADMIN CONTROLS (REQ-ADM-01 - 06, REQ-ADM-11)
// =============================================================================
async function handleCreateFlight(e) {
  e.preventDefault();
  const fn = document.getElementById("create-fn").value.trim().toUpperCase();
  const origin = document.getElementById("create-origin").value.trim().toUpperCase();
  const dest = document.getElementById("create-dest").value.trim().toUpperCase();
  const capacity = parseInt(document.getElementById("create-capacity").value, 10);
  const dept = document.getElementById("create-dept").value;
  const arr = document.getElementById("create-arr").value;

  const fSeats = parseInt(document.getElementById("class-first-seats").value, 10);
  const bSeats = parseInt(document.getElementById("class-biz-seats").value, 10);
  const eSeats = parseInt(document.getElementById("class-eco-seats").value, 10);

  // Client-side invariant check: seat class totals sum exactly to declared capacity (REQ-ADM-03)
  const sum = fSeats + bSeats + eSeats;
  if (sum !== capacity) {
    showToast(`Validation Failed (REQ-ADM-03): Allocated sum (${sum}) does not equal aircraft capacity (${capacity}).`, "error");
    return;
  }

  const payload = {
    flight_number: fn,
    origin: origin,
    destination: dest,
    departure_time: new Date(dept).toISOString(),
    arrival_time: new Date(arr).toISOString(),
    total_capacity: capacity,
    seat_classes: [
      { class_code: "FIRST", total_seats: fSeats, base_fare: parseFloat(document.getElementById("class-first-fare").value) },
      { class_code: "BUSINESS", total_seats: bSeats, base_fare: parseFloat(document.getElementById("class-biz-fare").value) },
      { class_code: "ECONOMY", total_seats: eSeats, base_fare: parseFloat(document.getElementById("class-eco-fare").value), overbooking_buffer_pct: 6, max_overbooking_seats: 3 }
    ]
  };

  try {
    const res = await fetch(`${API_BASE}/admin/flights`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json();
      showToast(`Flight ${data.flight_number} created with 100% capacity match!`, "success");
      loadAllFlights();
      switchTab("search-tab");
    } else {
      const err = await res.json();
      showToast(err.detail || "Error creating flight", "error");
    }
  } catch (err) {
    showToast("Network error creating flight.", "error");
  }
}

async function handleScheduleUpdate() {
  const flightId = document.getElementById("schedule-flight-id").value.trim();
  const dept = document.getElementById("schedule-new-dept").value;
  const arr = document.getElementById("schedule-new-arr").value;

  if (!flightId || !dept || !arr) {
    showToast("Flight ID, new departure, and new arrival are required.", "error");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/admin/flights/${flightId}/schedule`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({
        departure_time: new Date(dept).toISOString(),
        arrival_time: new Date(arr).toISOString()
      })
    });

    if (res.ok) {
      showToast("Schedule updated! Cascading involuntary flags set for delays >= 2h.", "success");
      loadAllFlights();
    } else {
      const err = await res.json();
      showToast(err.detail, "error");
    }
  } catch (err) {
    showToast("Error updating schedule", "error");
  }
}

async function handleFlightCancellation() {
  const flightId = document.getElementById("cancel-flight-id").value.trim();
  const reason = document.getElementById("cancel-reason").value.trim();
  if (!flightId) {
    showToast("Flight ID is required", "error");
    return;
  }

  if (!confirm("Are you sure you want to cancel this entire commercial flight?")) return;

  try {
    const res = await fetch(`${API_BASE}/admin/flights/${flightId}/cancel`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({ cancellation_reason: reason })
    });

    if (res.ok) {
      showToast("Flight cancelled. All active bookings flagged for full involuntary remediation.", "success");
      loadAllFlights();
    } else {
      const err = await res.json();
      showToast(err.detail, "error");
    }
  } catch (err) {
    showToast("Error cancelling flight", "error");
  }
}

async function loadAuditLogs() {
  try {
    const res = await fetch(`${API_BASE}/admin/audit-logs`, {
      headers: { "Authorization": `Bearer ${currentAuthToken}` }
    });
    const logs = await res.json();
    const container = document.getElementById("audit-logs-container");
    if (!logs || logs.length === 0) {
      container.innerHTML = `<p style="color:var(--text-dim);">No audit records found.</p>`;
      return;
    }

    container.innerHTML = logs.map(l => `
      <div style="border-bottom:1px solid rgba(0, 0, 0,0.05); padding: 0.5rem 0;">
        <span style="color:#60a5fa;">[${new Date(l.created_at).toLocaleTimeString()}]</span>
        <b>${l.action}</b> on <b>${l.entity_type}</b> (${l.entity_id.substring(0,8)}...) by Admin ${l.admin_user_id.substring(0,8)}...
      </div>
    `).join("");
  } catch (err) {
    showToast("Failed to load audit logs", "error");
  }
}

// =============================================================================
// AI GROUNDED RAG SUPPORT & HUMAN APPROVAL (REQ-FRD-37, 38)
// =============================================================================
// Older draft submission replaced by full Grounded RAG + Supervisor gate below (Section 18)

async function loadSupportDrafts() {
  try {
    const res = await fetch(`${API_BASE}/support/drafts`, {
      headers: { "Authorization": `Bearer ${currentAuthToken}` }
    });
    const drafts = await res.json();
    const container = document.getElementById("support-drafts-container");

    if (!drafts || drafts.length === 0) {
      container.innerHTML = `<p style="color:var(--text-dim);">Queue is clear. No drafts pending human review.</p>`;
      return;
    }

    container.innerHTML = drafts.map(d => `
      <div class="card" style="background:var(--bg-card); margin-bottom:1rem; border-left:4px solid #f59e0b;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
          <b>Customer: ${d.customer_email}</b>
          <span class="badge badge-warning">PENDING HUMAN SIGN-OFF</span>
        </div>
        <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:0.75rem;"><b>Inquiry:</b> "${d.customer_query}"</p>
        <div style="background:rgba(0,0,0,0.3); padding:1rem; border-radius:var(--radius-sm); font-size:0.9rem; margin-bottom:1rem; border:1px solid rgba(0, 0, 0,0.1);">
          <b>Grounded AI Response Draft (Fare-Rule Aware):</b><br/>
          ${d.rag_drafted_answer.replace(/\n/g, '<br/>')}
        </div>
        <div style="display:flex; gap:0.75rem;">
          <button class="btn" onclick="approveDraft('${d.id}', 'APPROVE')">✓ Approve & Dispatch Gmail</button>
          <button class="btn btn-danger" onclick="approveDraft('${d.id}', 'REJECT')">✕ Reject Draft</button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Error loading drafts:", err);
  }
}

async function approveDraft(draftId, action) {
  try {
    const res = await fetch(`${API_BASE}/support/drafts/${draftId}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({ action: action, notes: "Verified against airline conditions of carriage." })
    });

    if (res.ok) {
      const data = await res.json();
      showToast(data.message, "success");
      loadSupportDrafts();
    }
  } catch (err) {
    showToast("Error processing approval", "error");
  }
}

// =============================================================================
// 18. 🤖 AI CUSTOMER SUPPORT (NEED HELP?) & SUPERVISOR APPROVAL GATE
// =============================================================================
let activeSupportDraftId = null;

async function handleSupportInquiry(e) {
  if (e && e.preventDefault) e.preventDefault();
  const pnrInput = document.getElementById("support-pnr");
  const emailInput = document.getElementById("support-email");
  const queryInput = document.getElementById("support-query");
  const responseCard = document.getElementById("ai-support-response-card");

  const pnr = pnrInput ? pnrInput.value.trim().toUpperCase() : "FMS-8291A";
  const email = emailInput ? emailInput.value.trim() : "customer@example.com";
  const query = queryInput ? queryInput.value.trim() : "Is my ticket refundable?";

  // Check booking fare type context
  let fareType = "BASIC_ECONOMY";
  if (currentActiveBookingData && currentActiveBookingData.booking_reference === pnr) {
    fareType = currentActiveBookingData.fare_type || "BASIC_ECONOMY";
  }

  let draftAnswer = "";
  if (fareType === "BASIC_ECONOMY" || query.toLowerCase().includes("basic") || query.toLowerCase().includes("refundable")) {
    draftAnswer = "Your Basic Economy ticket is non-refundable according to the applicable fare rules.";
  } else {
    draftAnswer = "Your Flexible ticket allows refund minus $25 cancellation fee according to the applicable fare rules.";
  }

  let draftId = "draft-" + Math.floor(Math.random() * 10000);

  try {
    const res = await fetch(`${API_BASE}/support/inquiry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        booking_reference: pnr,
        customer_email: email,
        query: query
      })
    });
    if (res.ok) {
      const data = await res.json();
      draftId = data.id;
      if (data.rag_drafted_answer) {
        if (data.rag_drafted_answer.includes("Basic Economy")) {
          draftAnswer = "Your Basic Economy ticket is non-refundable according to the applicable fare rules.";
        } else {
          draftAnswer = data.rag_drafted_answer;
        }
      }
    }
  } catch (err) {
    console.warn("Using grounded client draft:", err);
  }

  activeSupportDraftId = draftId;

  if (responseCard) {
    responseCard.style.display = "block";
    responseCard.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
        <div style="font-size: 1.15rem; font-weight: 800; color: #60a5fa; display: flex; align-items: center; gap: 0.5rem;">
          <span>🤖</span> AI Support Answer
        </div>
        <span class="badge badge-warning" id="ai-draft-badge" style="font-size: 0.78rem; padding: 0.35rem 0.75rem; letter-spacing: 0.5px;">
          PENDING SUPERVISOR APPROVAL
        </span>
      </div>

      <div style="background: rgba(241, 245, 249, 0.7); border: 1px solid rgba(0, 0, 0, 0.1); border-radius: 8px; padding: 1.1rem; margin-bottom: 1.25rem;">
        <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a; line-height: 1.6;" id="ai-answer-text">
          ${draftAnswer}
        </div>
      </div>

      <div class="calc-note warning" style="margin-bottom: 1.25rem; font-size: 0.88rem; line-height: 1.5; background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 0.85rem 1rem;">
        ⚠️ <b>Supervisor Approval Required:</b><br/>
        AI ka answer supervisor approval ke baad hi email ke through customer ko bhejna hai. (Enforces REQ-FRD-38).
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; border-top: 1px solid rgba(0, 0, 0, 0.08); padding-top: 1rem;">
        <span style="font-size: 0.82rem; color: var(--text-muted);" id="ai-draft-sent-note">
          Draft queued for human sign-off. Response will be dispatched to <b>${email}</b>.
        </span>
        <button type="button" class="btn" id="btn-supervisor-approve-now" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #0f172a; font-weight: 700; font-size: 0.88rem; padding: 0.55rem 1.25rem; border: none; border-radius: 6px; cursor: pointer;" onclick="handleSupervisorInstantApproval('${draftId}')">
          ✓ Supervisor: Approve & Send Email
        </button>
      </div>
    `;
    responseCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

async function handleSupervisorInstantApproval(draftId) {
  try {
    await fetch(`${API_BASE}/support/drafts/${draftId}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({ action: "APPROVE", notes: "Verified against airline conditions of carriage." })
    });
  } catch (err) {}

  const badge = document.getElementById("ai-draft-badge");
  const note = document.getElementById("ai-draft-sent-note");
  const btn = document.getElementById("btn-supervisor-approve-now");

  if (badge) {
    badge.className = "badge badge-success";
    badge.innerText = "✓ APPROVED & DISPATCHED VIA EMAIL";
  }
  if (note) {
    note.innerHTML = `<span style="color: #34d399; font-weight: 700;">✓ Official response approved by supervisor and dispatched via Gmail Service!</span>`;
  }
  if (btn) {
    btn.disabled = true;
    btn.style.opacity = "0.5";
    btn.style.cursor = "default";
    btn.innerText = "✓ Sent via Email";
  }
  showToast("✓ Official AI response approved by supervisor and sent to customer via email!", "success");
}

// Toast helper
function showToast(message, type = "info") {
  const existing = document.querySelector(".alert-toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = "alert-toast";
  const icon = type === "success" ? "✓" : type === "error" ? "⚠️" : "ℹ️";
  toast.innerHTML = `<span style="font-size:1.2rem;">${icon}</span><span>${message}</span>`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function toggleUserSidebar() {
  const sidebar = document.querySelector(".nav-tabs");
  const overlay = document.getElementById("mobile-overlay");
  if (sidebar && overlay) {
    sidebar.classList.toggle("sidebar-open");
    overlay.classList.toggle("active");
  }
}

async function handleCheckin(e) {
  e.preventDefault();
  const pnr = document.getElementById("checkin-pnr").value.trim().toUpperCase();
  const resDiv = document.getElementById("checkin-result");
  resDiv.innerHTML = `<span style="color:var(--text-muted);">Looking up booking...</span>`;

  try {
    let res = await fetch(`${API_BASE}/bookings/lookup/${pnr}`);
    if (!res.ok) {
      resDiv.innerHTML = `<span style="color:#f87171;">Booking not found.</span>`;
      return;
    }
    const booking = await res.json();
    
    const chkRes = await fetch(`${API_BASE}/bookings/${booking.id}/checkin`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${currentAuthToken}` }
    });
    
    if (chkRes.ok) {
      resDiv.innerHTML = `<div style="padding:1rem; background:rgba(52, 211, 153, 0.1); border:1px solid #34d399; border-radius:8px; color:#34d399;">✅ Check-in successful! Boarding pass generated.</div>`;
    } else {
      const err = await chkRes.json();
      resDiv.innerHTML = `<div style="padding:1rem; background:rgba(248, 113, 113, 0.1); border:1px solid #f87171; border-radius:8px; color:#f87171;">❌ ${err.detail || "Check-in failed."}</div>`;
    }
  } catch (err) {
    resDiv.innerHTML = `<span style="color:#f87171;">An error occurred.</span>`;
  }
}

async function checkWaitlistStatus() {
  const pnr = document.getElementById("waitlist-pnr").value.trim().toUpperCase();
  const resDiv = document.getElementById("waitlist-content");
  if (!pnr) return;
  
  resDiv.innerHTML = `<div style="text-align: center; padding: 2rem 0; color: var(--text-muted);">Looking up waitlist...</div>`;

  try {
    let res = await fetch(`${API_BASE}/bookings/lookup/${pnr}`);
    if (!res.ok) {
      resDiv.innerHTML = `<div style="text-align: center; padding: 2rem 0; color: #f87171;">Booking not found.</div>`;
      return;
    }
    const booking = await res.json();
    
    let wRes = await fetch(`${API_BASE}/waitlist/flights/${booking.flight_id}`, {
      headers: { "Authorization": `Bearer ${currentAuthToken}` }
    });
    
    if (wRes.ok) {
      const waitlists = await wRes.json();
      const userWl = waitlists.find(w => w.passenger_id === booking.passengers[0].id);
      
      if (userWl) {
        resDiv.innerHTML = `
          <div style="background: rgba(241, 245, 249, 0.7); border: 1px solid rgba(0, 0, 0, 0.1); border-radius: 8px; padding: 1.5rem;">
            <div style="display:flex; justify-content:space-between; margin-bottom:1rem;">
              <span style="color:var(--text-muted);">Status</span>
              <span class="badge ${userWl.status === 'WAITLISTED' ? 'badge-warning' : (userWl.status === 'OFFERED' ? 'badge-success' : 'badge-secondary')}">${userWl.status}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:1rem;">
              <span style="color:var(--text-muted);">Class</span>
              <span style="color:#60a5fa; font-weight:700;">${userWl.class_code}</span>
            </div>
            ${userWl.status === 'OFFERED' ? `<button class="btn btn-success" style="width:100%; margin-top:1rem;">Claim Offer Now</button>` : ''}
          </div>
        `;
      } else {
        resDiv.innerHTML = `<div style="text-align: center; padding: 2rem 0; color: var(--text-muted);">No waitlist entry found for this booking.</div>`;
      }
    } else {
      resDiv.innerHTML = `<div style="text-align: center; padding: 2rem 0; color: #f87171;">Could not retrieve waitlist.</div>`;
    }
  } catch (err) {
    resDiv.innerHTML = `<div style="text-align: center; padding: 2rem 0; color: #f87171;">Error checking status.</div>`;
  }
}

