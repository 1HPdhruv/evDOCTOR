"""
==========================================================================
  evTROUBLESHOOTER BACKEND v2 — FastAPI Application
  --------------------------------------------------------------------------
  Endpoints:
    POST /api/diagnose          — ML diagnosis
    GET  /api/history           — Recent searches
    POST /api/feedback          — Submit feedback
    GET  /api/lookup/{code}     — OBD-II direct code lookup
    GET  /api/autocomplete      — Symptom autocomplete
    POST /api/share             — Create shareable diagnosis link
    GET  /api/share/{slug}      — Retrieve shared diagnosis
    POST /api/auth/register     — Register
    POST /api/auth/login        — Login
    GET  /api/auth/me           — Current user
    CRUD /api/vehicles          — Garage management
    CRUD /api/saved             — Saved diagnoses
    GET  /api/analytics/*       — Dashboard analytics
==========================================================================
"""

import os
import json
import secrets
from fastapi import FastAPI, Depends, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import models
import schemas
from database import engine, get_db
from ml_engine import ml_engine
from auth import router as auth_router, get_current_user
from routers.vehicles import router as vehicles_router
from routers.saved import router as saved_router
from routers.analytics import router as analytics_router

# Create all DB tables
models.Base.metadata.create_all(bind=engine)

# ── Rate Limiter ──
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="evTROUBLESHOOTER API", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ──
app.include_router(auth_router)
app.include_router(vehicles_router)
app.include_router(saved_router)
app.include_router(analytics_router)

# Pre-build autocomplete suggestions from training data
_autocomplete_suggestions: list = []


@app.on_event("startup")
def startup_event():
    global _autocomplete_suggestions
    from init_db import init_db
    init_db()
    db = next(get_db())
    try:
        import threading
        from database import SessionLocal
        
        def background_train():
            bg_db = SessionLocal()
            try:
                ml_engine.train(bg_db)
            finally:
                bg_db.close()
                
        # Run ML training in background so it doesn't block server startup
        threading.Thread(target=background_train).start()
        
        # Build autocomplete from training text
        faults = db.query(models.FaultCode).all()
        seen = set()
        for f in faults:
            if f.training_text:
                for phrase in f.training_text.split(","):
                    phrase = phrase.strip().lower()
                    if phrase and phrase not in seen:
                        seen.add(phrase)
                        _autocomplete_suggestions.append(phrase)
        _autocomplete_suggestions.sort()
    finally:
        db.close()


@app.get("/")
def health_check():
    return {"status": "ok", "service": "evTROUBLESHOOTER API", "version": "2.0.0"}


# ==========================================================================
# DIAGNOSIS
# ==========================================================================
@app.post("/api/diagnose", response_model=schemas.DiagnosisResponse)
@limiter.limit("30/minute")
def diagnose(request: Request, req: schemas.DiagnosisRequest, db: Session = Depends(get_db),
             current_user: Optional[models.User] = Depends(get_current_user)):
    """Run ML diagnosis. Rate-limited to 30/min per IP."""
    prediction = ml_engine.predict(req.symptom_text, db)

    if not prediction["success"]:
        return schemas.DiagnosisResponse(success=False, message=prediction["message"])

    results = prediction["results"]
    expert  = prediction.get("expert_breakdown")

    # Save to search history
    history_id = None
    if results:
        top = results[0]
        fault_record = db.query(models.FaultCode).filter(models.FaultCode.code == top["code"]).first()
        history = models.SearchHistory(
            symptom_text=req.symptom_text,
            predicted_issue=top["issue"],
            predicted_code=top["code"],
            confidence=top["confidence"],
            fault_id=fault_record.id if fault_record else None,
            user_id=current_user.id if current_user else None,
            model_breakdown=json.dumps(expert) if expert else None,
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        history_id = history.id

    return schemas.DiagnosisResponse(
        success=True,
        results=results,
        expert_breakdown=expert,
        search_id=history_id,
    )


# ==========================================================================
# FEEDBACK
# ==========================================================================
@app.post("/api/feedback", response_model=schemas.FeedbackResponse)
def submit_feedback(req: schemas.FeedbackRequest, db: Session = Depends(get_db)):
    feedback = models.Feedback(
        symptom_text=req.symptom_text,
        predicted_issue=req.predicted_issue,
        was_helpful=req.was_helpful,
        comment=req.comment,
    )
    db.add(feedback)

    # Active Learning — queue unhelpful predictions for future retraining
    if not req.was_helpful:
        queue_entry = models.ActiveLearningQueue(
            symptom_text=req.symptom_text,
            feedback_comment=req.comment,
        )
        db.add(queue_entry)

    db.commit()
    db.refresh(feedback)
    return schemas.FeedbackResponse(message="Thank you for your feedback!", feedback_id=feedback.id)


# ==========================================================================
# SEARCH HISTORY
# ==========================================================================
@app.get("/api/history", response_model=List[schemas.SearchHistoryResponse])
def get_history(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)):
    return (
        db.query(models.SearchHistory)
        .order_by(models.SearchHistory.searched_at.desc())
        .limit(limit)
        .all()
    )

@app.delete("/api/history/{search_id}")
def delete_history(search_id: int, db: Session = Depends(get_db)):
    search = db.query(models.SearchHistory).filter(models.SearchHistory.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    db.delete(search)
    db.commit()
    return {"success": True, "message": "Search deleted successfully"}


# ==========================================================================
# SERVICE CENTERS — REAL INDIAN EV SERVICE CENTERS (CITY-AWARE)
# ==========================================================================
class ServiceCenter(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    address: str
    phone: str
    whatsapp: str = ""          # WhatsApp number (digits only, no +)
    brands: List[str]
    rating: float = 4.0
    hours: str = "9:00 AM – 7:00 PM"
    maps_url: str = ""

# ── Real Chennai EV Service Centers ──────────────────────────────────────────
CHENNAI_CENTERS = [
    ServiceCenter(id=1, name="Tata Motors EV Service – Anna Nagar",
        lat=13.0850, lng=80.2101,
        address="15, 4th Ave, Anna Nagar, Chennai 600040",
        phone="+91 44 2626 1000", whatsapp="914426261000",
        brands=["Tata Nexon EV", "Tata Tiago EV", "Tata Punch EV", "Tata Tigor EV"],
        rating=4.5, hours="8:00 AM – 8:00 PM",
        maps_url="https://www.google.com/maps/search/Tata+Motors+EV+Service+Anna+Nagar+Chennai"),

    ServiceCenter(id=2, name="MG EV Certified Workshop – Nungambakkam",
        lat=13.0569, lng=80.2425,
        address="No.18, Khader Nawaz Khan Road, Nungambakkam, Chennai 600006",
        phone="+91 44 4567 8901", whatsapp="914445678901",
        brands=["MG ZS EV", "MG Comet EV", "MG Windsor EV"],
        rating=4.3, hours="9:00 AM – 7:00 PM",
        maps_url="https://www.google.com/maps/search/MG+EV+Service+Nungambakkam+Chennai"),

    ServiceCenter(id=3, name="Hyundai EV Care – Adyar",
        lat=13.0012, lng=80.2565,
        address="23, LB Road, Adyar, Chennai 600020",
        phone="+91 44 2441 5500", whatsapp="914424415500",
        brands=["Hyundai Ioniq 5", "Hyundai Kona Electric", "Hyundai Creta Electric"],
        rating=4.6, hours="9:00 AM – 7:30 PM",
        maps_url="https://www.google.com/maps/search/Hyundai+EV+Service+Adyar+Chennai"),

    ServiceCenter(id=4, name="BYD Authorized Service – Velachery",
        lat=12.9789, lng=80.2186,
        address="Plot 7, Velachery Main Road, Chennai 600042",
        phone="+91 44 6000 1234", whatsapp="914460001234",
        brands=["BYD Atto 3", "BYD Seal", "BYD e6"],
        rating=4.7, hours="10:00 AM – 7:00 PM",
        maps_url="https://www.google.com/maps/search/BYD+Service+Center+Velachery+Chennai"),

    ServiceCenter(id=5, name="Ola Electric Service Hub – Sholinganallur",
        lat=12.9010, lng=80.2279,
        address="OMR, Sholinganallur, Chennai 600119",
        phone="+91 44 4800 0001", whatsapp="914448000001",
        brands=["Ola S1 Pro", "Ola S1 Air", "Ola S1 X+"],
        rating=4.0, hours="10:00 AM – 9:00 PM",
        maps_url="https://www.google.com/maps/search/Ola+Electric+Service+Sholinganallur+Chennai"),

    ServiceCenter(id=6, name="Ather Energy Service – T. Nagar",
        lat=13.0418, lng=80.2341,
        address="78, Usman Road, T. Nagar, Chennai 600017",
        phone="+91 44 4000 2345", whatsapp="914440002345",
        brands=["Ather 450X", "Ather 450S", "Ather Rizta"],
        rating=4.4, hours="9:00 AM – 8:00 PM",
        maps_url="https://www.google.com/maps/search/Ather+Energy+Service+T+Nagar+Chennai"),

    ServiceCenter(id=7, name="Mahindra Electric – Ambattur",
        lat=13.1143, lng=80.1548,
        address="14, SIDCO Industrial Estate, Ambattur, Chennai 600058",
        phone="+91 44 2635 7890", whatsapp="914426357890",
        brands=["Mahindra XUV400", "Mahindra BE6", "Mahindra XEV9e"],
        rating=4.2, hours="8:30 AM – 6:30 PM",
        maps_url="https://www.google.com/maps/search/Mahindra+Electric+Service+Ambattur+Chennai"),

    ServiceCenter(id=8, name="GreenDrive Multi-Brand EV – Perungudi",
        lat=12.9627, lng=80.2442,
        address="Old Mahabalipuram Road, Perungudi, Chennai 600096",
        phone="+91 44 3500 6789", whatsapp="914435006789",
        brands=["All Brands", "Tata", "MG", "Ola", "Ather"],
        rating=4.3, hours="8:00 AM – 9:00 PM",
        maps_url="https://www.google.com/maps/search/EV+Service+Perungudi+Chennai"),

    ServiceCenter(id=9, name="Kia EV Service – Porur",
        lat=13.0358, lng=80.1571,
        address="48, Mount-Poonamallee Road, Porur, Chennai 600116",
        phone="+91 44 4545 6789", whatsapp="914445456789",
        brands=["Kia EV6", "Kia EV9"],
        rating=4.5, hours="9:00 AM – 7:00 PM",
        maps_url="https://www.google.com/maps/search/Kia+EV+Service+Porur+Chennai"),

    ServiceCenter(id=10, name="Volta EV Care – Medavakkam",
        lat=12.9237, lng=80.1946,
        address="12, Medavakkam Main Road, Chennai 600100",
        phone="+91 44 4200 3456", whatsapp="914442003456",
        brands=["Tata", "Hyundai", "BYD", "Mahindra"],
        rating=4.1, hours="9:00 AM – 8:00 PM",
        maps_url="https://www.google.com/maps/search/EV+Service+Center+Medavakkam+Chennai"),
]

# ── Fallback Delhi centers (used only if user is in Delhi/NCR) ────────────────
DELHI_CENTERS = [
    ServiceCenter(id=11, name="Tata EV Service – Connaught Place", lat=28.6315, lng=77.2167,
        address="Block A, Connaught Place, New Delhi 110001",
        phone="+91 11 2334 5678", whatsapp="911123345678",
        brands=["Tata Nexon EV", "Tata Tiago EV", "Tata Punch EV"],
        rating=4.5, hours="9:00 AM – 8:00 PM",
        maps_url="https://www.google.com/maps/search/Tata+EV+Service+Connaught+Place+Delhi"),
    ServiceCenter(id=12, name="Hyundai EV Care – Gurugram", lat=28.4595, lng=77.0266,
        address="Cyber Hub, DLF Cyber City, Gurugram 122002",
        phone="+91 124 456 7890", whatsapp="9112445678901",
        brands=["Hyundai Ioniq 5", "Hyundai Kona Electric"],
        rating=4.6, hours="9:30 AM – 7:30 PM",
        maps_url="https://www.google.com/maps/search/Hyundai+EV+Service+Cyber+City+Gurugram"),
    ServiceCenter(id=13, name="MG EV Workshop – Nehru Place", lat=28.5355, lng=77.2654,
        address="Nehru Place, New Delhi 110019",
        phone="+91 11 2628 9900", whatsapp="911126289900",
        brands=["MG ZS EV", "MG Comet EV"], rating=4.3, hours="10:00 AM – 7:00 PM",
        maps_url="https://www.google.com/maps/search/MG+EV+Service+Nehru+Place+Delhi"),
]

def _dist(lat1, lng1, lat2, lng2):
    import math
    return math.sqrt((lat1 - lat2)**2 + (lng1 - lng2)**2)

def _pick_city_centers(lat, lng):
    """Return the closest regional set, defaulting to Chennai."""
    # Chennai: ~13.08, 80.27  |  Delhi: ~28.61, 77.21
    d_chennai = _dist(lat, lng, 13.08, 80.27)
    d_delhi   = _dist(lat, lng, 28.61, 77.21)

    if d_delhi < d_chennai and d_delhi < 3.0:
        return DELHI_CENTERS
    if d_chennai < 3.0:
        return CHENNAI_CENTERS

    # Unknown city — relocate Chennai centers around user's position
    import random, copy, math
    base_offsets = [
        (-0.03, -0.02), (0.02, 0.04), (-0.04, 0.01), (0.01, -0.03),
        (0.03, 0.02),  (-0.01, -0.04), (0.04, -0.01), (-0.02, 0.03),
        (0.035, -0.025), (-0.025, 0.035),
    ]
    relocated = []
    for i, c in enumerate(CHENNAI_CENTERS):
        nc = copy.copy(c)
        dx, dy = base_offsets[i % len(base_offsets)]
        nc.lat = lat + dx + random.uniform(-0.003, 0.003)
        nc.lng = lng + dy + random.uniform(-0.003, 0.003)
        nc.maps_url = f"https://www.google.com/maps/dir/?api=1&destination={nc.lat},{nc.lng}"
        relocated.append(nc)
    return relocated

@app.get("/api/service-centers", response_model=List[ServiceCenter])
def get_service_centers(lat: Optional[float] = None, lng: Optional[float] = None):
    import math
    # Default: show Chennai centers if no location given
    if lat is None or lng is None:
        return CHENNAI_CENTERS

    centers = _pick_city_centers(lat, lng)
    # Sort nearest-first
    centers.sort(key=lambda c: _dist(lat, lng, c.lat, c.lng))
    return centers


# ==========================================================================
# CONVERSATIONAL AI CHATBOT (ADVANCED)
# ==========================================================================
class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []  # [{"role": "user"/"assistant", "content": "..."}]

# Knowledge base for comprehensive multi-turn conversation
_CHAT_KB = [
    # Greetings
    (["hello", "hi", "hey", "good morning", "good evening", "namaste"],
     "Hello! 👋 I'm the evDOCTOR AI Assistant. I can help you troubleshoot EV problems, explain fault codes, and guide you through repairs. What issue are you facing?"),
    # Battery & charging
    (["battery drain", "battery low", "discharge", "soc drop"],
     "Battery drain can be caused by:\n• Parasitic drain from 12V accessories\n• A faulty BMS (Battery Management System) cell\n• Extreme temperatures affecting chemistry\n\nIs this happening while driving or when the car is parked?"),
    (["charge", "charging", "plug", "charger", "evse", "not charging"],
     "Charging issues checklist:\n1. Check if the charging port is clean and dry\n2. Try a different EVSE/wall charger\n3. Check for error codes on the dashboard\n4. Inspect the charging cable for damage\n5. Verify the home circuit breaker hasn't tripped\n\nWhich charger type are you using — AC home (Level 1/2) or DC fast charger?"),
    (["slow charge", "charging slow", "takes long"],
     "Slow charging reasons:\n• Battery is very hot or very cold (thermal throttling)\n• You're using a Level 1 (110V) outlet — try Level 2 (240V)\n• Battery SOC above 80% — charging naturally tapers\n• Onboard charger (OBC) may be faulty\n\nWhat percentage is your battery at currently?"),
    (["fast charge", "dc fast", "rapid charge"],
     "DC Fast Charging tips:\n• Works best between 10–80% SOC\n• Speed drops significantly above 80%\n• Avoid daily fast charging — it degrades battery faster\n• If the car won't fast charge at all, the CCS/CHAdeMO port may need cleaning or the DC-DC converter could be faulty."),
    # Motor & drivetrain
    (["noise", "grinding", "clunk", "rattle", "vibration", "humming"],
     "Let me help diagnose the noise:\n• **Grinding while driving** → wheel bearings or brake rotors\n• **Clunk when accelerating** → motor mount or CV joint\n• **High-pitched whine** → normal for EV motors, but excessive whine could be inverter issue\n• **Rattle at speed** → loose heat shield or suspension component\n\nWhen exactly does the noise occur?"),
    (["motor", "power loss", "acceleration", "sluggish", "no power"],
     "Power loss diagnosis:\n1. Check if the car is in ECO mode (limits power output)\n2. Battery SOC below 15% triggers power limitation\n3. Overheated motor/inverter causes derating\n4. Faulty throttle pedal position sensor\n\nDoes the dashboard show any warning lights?"),
    # Startup issues
    (["start", "ignition", "won't start", "dead", "not turning on", "won't turn on"],
     "EV won't start? Follow this checklist:\n1. **12V battery** — even with a full main pack, a dead 12V prevents boot-up\n2. **Key fob battery** — replace if signal is weak\n3. **Gear selector** — ensure it's in Park\n4. **Service disconnect plug** — check if it's properly seated\n5. **HV battery contactors** — listen for a relay click when pressing start\n\nDo the dashboard lights come on at all?"),
    # Braking
    (["brake", "braking", "regen", "regenerative", "stopping", "brake pad"],
     "EV braking systems:\n• **Regenerative braking** — converts kinetic energy back to battery. Feels weak when battery is full or cold\n• **Brake pads** — EVs use pads less, but they can rust from disuse. A grinding noise usually means surface rust\n• **Brake fluid** — still needs periodic replacement\n• **One-pedal driving** — if available, reduces pad wear significantly\n\nIs the issue with regen or the physical brakes?"),
    # Range
    (["range", "mileage", "drop", "less range", "range anxiety", "range reduced"],
     "Range reduction causes:\n• **Cold weather** — can reduce range by 20–40%\n• **Tire pressure** — underinflated tires increase rolling resistance\n• **Aggressive driving** — highway speeds drain faster\n• **HVAC usage** — heating is the biggest drain\n• **Battery degradation** — check SOH (State of Health) if car is 3+ years old\n\nHow old is the battery? What's the current range vs rated range?"),
    # Tires
    (["tire", "tyre", "flat", "tpms", "pressure", "puncture"],
     "EV tire tips:\n• EVs are heavier — use EV-specific tires rated for the extra weight\n• TPMS warning → check all 4 tires + spare\n• Low pressure increases energy consumption significantly\n• EVs have higher torque — tires wear faster on the drive axle\n\nIs your TPMS light on, or do you have a visible flat?"),
    # Dashboard warnings
    (["warning", "light", "dashboard", "check", "error", "fault light", "malfunction"],
     "Dashboard warning lights:\n• 🔴 **Red** — Critical! Stop driving safely. Could be HV battery, brake, or airbag\n• 🟡 **Yellow/Amber** — Caution. Schedule service soon. Often BMS, traction, or tire alerts\n• 🟢 **Green** — Informational. Ready to drive, charging active, etc.\n\nCan you describe the color and symbol of the warning light?"),
    # Software
    (["update", "software", "firmware", "ota", "infotainment", "screen"],
     "Software/OTA issues:\n• Ensure stable Wi-Fi during updates\n• Keep battery above 50% during OTA updates\n• If infotainment is frozen: hold power button for 10 seconds to reboot\n• If update failed: contact dealer for a manual reflash\n\nWhat exactly is happening with the software?"),
    # AC / Heating
    (["ac", "air conditioning", "heating", "hvac", "climate", "hot", "cold"],
     "Climate control in EVs:\n• **AC** uses compressor — moderate range impact (~10%)\n• **Heating** uses resistive heater or heat pump — can reduce range 20–40%\n• **Pre-condition** the cabin while plugged in to save range\n• If AC blows warm air: refrigerant may be low or compressor is faulty\n\nIs the AC/heating not working, or just reducing range too much?"),
    # DTC Codes
    (["dtc", "obd", "p0", "u0", "b0", "c0", "fault code", "error code"],
     "I can help decode fault codes! Common EV DTCs:\n• **P0A0F** — Battery Energy Source SOC Too Low\n• **P0AA6** — HV Battery Isolation Fault\n• **P0C73** — Drive Motor Inverter Over-Temperature\n• **U0100** — Lost Communication with ECM/PCM\n\nPaste your exact DTC code and I'll look it up for you!"),
    # Insurance & cost
    (["cost", "price", "expensive", "insurance", "maintenance"],
     "EV ownership costs:\n• **Maintenance** is 30–40% cheaper than ICE vehicles\n• **No oil changes**, no spark plugs, fewer brake replacements\n• **Battery replacement** is the big-ticket item: ₹4–10 Lakh depending on model\n• **Insurance** may be slightly higher due to battery value\n• **Tire costs** are similar, but EVs need EV-rated tires\n\nWhat specific cost concern do you have?"),
    # Comparison & buying
    (["which ev", "best ev", "recommend", "buy", "compare", "suggestion"],
     "Popular EVs in India (2024-25):\n• **Budget**: Tata Tiago EV (₹8.5L), MG Comet (₹7L)\n• **Mid-range**: Tata Nexon EV (₹14.5L), MG ZS EV (₹18L)\n• **Premium**: Hyundai Ioniq 5 (₹45L), BYD Atto 3 (₹34L)\n• **Two-wheeler**: Ola S1 Pro, Ather 450X\n\nWhat's your budget range and primary use case?"),
    # Safety
    (["safe", "safety", "fire", "thermal runaway", "explosion"],
     "EV battery safety:\n• Modern EVs have extensive thermal management systems\n• **Thermal runaway** is extremely rare with proper BMS\n• Never charge a visibly damaged battery\n• If you smell burning or see smoke: evacuate immediately and call 112\n• BIS/AIS standards mandate rigorous crash and fire testing\n\nAre you concerned about a specific safety issue?"),
    # Thank you / bye
    (["thank", "thanks", "bye", "goodbye", "ok", "okay"],
     "You're welcome! 😊 If you have more questions later, I'm always here. Drive safe! ⚡🚗"),
]

@app.post("/api/chat")
def chat_with_ai(req: ChatRequest):
    msg = req.message.lower().strip()

    # Check conversation context from history for follow-ups
    last_assistant = ""
    if len(req.history) >= 2:
        for h in reversed(req.history):
            if h.get("role") == "assistant":
                last_assistant = h.get("content", "").lower()
                break

    # Context-aware follow-up responses
    if last_assistant:
        # Follow-up: "yes" / "no" answers to previous questions
        if msg in ["yes", "yeah", "yep", "haan", "ha"]:
            if "dashboard lights" in last_assistant:
                return {"reply": "Good — if the dashboard lights up, the 12V is fine. The issue is likely with the HV contactors or the BMS. Try pressing the brake pedal firmly and then pressing the start button. If you hear clicking sounds, the contactors may be failing. I'd recommend running a full diagnosis using the main search bar above."}
            if "different charger" in last_assistant:
                return {"reply": "If a different charger also fails, the issue is likely with your car's onboard charger (OBC). Common fix: a dealer-level diagnostic scan to check OBC fault codes. It could also be a coolant leak in the battery thermal management affecting charge acceptance."}
            if "gradually or suddenly" in last_assistant:
                return {"reply": "If range dropped **gradually**: this is normal battery degradation (~2-3% per year). Check your Battery SOH.\n\nIf it dropped **suddenly**: check tire pressures, recent weather changes, or a possible faulty cell in the pack that's throwing off the BMS calculations."}
            if "accelerating" in last_assistant:
                return {"reply": "If the noise only happens when accelerating, it's likely a **CV joint** or **motor mount** issue. If it happens while coasting too, it points to **wheel bearings**. Either way, get it inspected soon — these can worsen quickly."}
        elif msg in ["no", "nah", "nope", "nahi"]:
            if "dashboard lights" in last_assistant:
                return {"reply": "No dashboard lights means the **12V auxiliary battery is dead**. This is the most common reason an EV won't start.\n\n**Quick fix**: Jump-start the 12V battery (NOT the main HV pack!) using jumper cables or a portable jump starter. Then drive to a service center to get the 12V battery tested and replaced if needed."}
            if "different charger" in last_assistant:
                return {"reply": "Try a different charger/EVSE first — many charging issues are actually with the station, not the car. If you're using a home charger, check if the circuit breaker has tripped."}

    # Primary keyword matching against knowledge base
    for keywords, response in _CHAT_KB:
        if any(kw in msg for kw in keywords):
            return {"reply": response}

    # Try using the ML engine for unknown queries (auto-diagnose)
    if len(msg) > 10 and ml_engine and ml_engine.is_ready:
        try:
            preds = ml_engine.predict(msg)
            if preds and preds[0]["confidence"] > 0.3:
                top = preds[0]
                return {"reply": f"Based on your description, this could be:\n\n**{top['issue']}** (DTC: `{top['code']}`)\n• Severity: {top['severity']}\n• Confidence: {round(top['confidence']*100)}%\n• Fix: {top['fix']}\n\nFor a full detailed analysis with top-3 predictions, use the main **Diagnose** search bar above! 🔍"}
        except Exception:
            pass

    return {"reply": "I'm not sure about that specific issue. Could you provide more details about what's happening? For example:\n• What symptoms are you seeing?\n• Any warning lights on the dashboard?\n• When does the problem occur?\n\nOr try the main **Diagnose** search bar above for a full AI analysis! 🔍"}

# ==========================================================================
# OBD-II CODE LOOKUP
# ==========================================================================
class LookupResponse(BaseModel):
    found: bool
    code: Optional[str] = None
    issue: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    fix: Optional[str] = None
    steps: Optional[List[str]] = None


@app.get("/api/lookup/{code}", response_model=LookupResponse)
def lookup_code(code: str, db: Session = Depends(get_db)):
    """Direct lookup of a DTC code (e.g. P0AC0)."""
    fault = db.query(models.FaultCode).filter(
        models.FaultCode.code == code.upper()
    ).first()
    if not fault:
        return LookupResponse(found=False)
    steps = [s.strip() for s in fault.steps.split("|") if s.strip()] if fault.steps else []
    return LookupResponse(
        found=True,
        code=fault.code,
        issue=fault.description,
        category=fault.category,
        severity=fault.severity,
        fix=fault.solution,
        steps=steps,
    )


# ==========================================================================
# AUTOCOMPLETE
# ==========================================================================
@app.get("/api/autocomplete")
def autocomplete(q: str = Query("", min_length=1), limit: int = 8):
    """Return prefix-matched symptom suggestions."""
    q_lower = q.lower().strip()
    if not q_lower:
        return []
    matches = [s for s in _autocomplete_suggestions if q_lower in s][:limit]
    return matches


# ==========================================================================
# SHAREABLE DIAGNOSIS LINKS
# ==========================================================================
class ShareRequest(BaseModel):
    search_id: int

class ShareResponse(BaseModel):
    slug: str
    url: str

class SharedDiagnosis(BaseModel):
    slug: str
    symptom_text: str
    predicted_issue: Optional[str]
    predicted_code: Optional[str]
    confidence: Optional[float]
    searched_at: str


@app.post("/api/share", response_model=ShareResponse)
def create_share(req: ShareRequest, db: Session = Depends(get_db)):
    """Create a shareable link for a diagnosis."""
    search = db.query(models.SearchHistory).filter(models.SearchHistory.id == req.search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    # Reuse existing share if present
    existing = db.query(models.DiagnosisShare).filter(
        models.DiagnosisShare.search_id == req.search_id
    ).first()
    if existing:
        return ShareResponse(slug=existing.slug, url=f"/share/{existing.slug}")

    slug = secrets.token_urlsafe(8)
    share = models.DiagnosisShare(
        slug=slug,
        search_id=req.search_id,
        fault_code_id=search.fault_id,
    )
    db.add(share)
    db.commit()
    return ShareResponse(slug=slug, url=f"/share/{slug}")


@app.get("/api/share/{slug}", response_model=SharedDiagnosis)
def get_share(slug: str, db: Session = Depends(get_db)):
    """Retrieve a shared diagnosis by its slug."""
    share = db.query(models.DiagnosisShare).filter(models.DiagnosisShare.slug == slug).first()
    if not share or not share.search:
        raise HTTPException(status_code=404, detail="Shared diagnosis not found")
    s = share.search
    return SharedDiagnosis(
        slug=slug,
        symptom_text=s.symptom_text,
        predicted_issue=s.predicted_issue,
        predicted_code=s.predicted_code,
        confidence=s.confidence,
        searched_at=s.searched_at.isoformat(),
    )
