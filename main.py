from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pymongo import MongoClient
from datetime import datetime
import os, io, shutil, urllib.parse

# ===================== REPORTLAB =====================
from reportlab.lib.pagesizes import A7, landscape
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ===================== APP =====================
app = FastAPI()

# ===================== CORS =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://pol-ui.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== DIRECTORIES =====================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ===================== DATABASE =====================
USERNAME = "pasumaibharatam_db_user"
PASSWORD = urllib.parse.quote_plus("pasumai123")
CLUSTER = "pasumai.mrsonfr.mongodb.net"

MONGO_URL = f"mongodb+srv://{USERNAME}:{PASSWORD}@{CLUSTER}/?retryWrites=true&w=majority"

client = MongoClient(MONGO_URL)
db = client["political_db"]
candidates = db["candidates"]

# ===================== MEMBERSHIP NO =====================
def generate_membership_no():
    count = candidates.count_documents({})
    return f"PBM-{datetime.now().year}-{count + 1:06d}"

# ===================== REGISTER =====================
@app.post("/register")
async def register(
    name: str = Form(...),
    father_name: str = Form(""),
    gender: str = Form(""),
    dob: str = Form(""),
    age: int = Form(...),
    blood_group: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(""),
    state: str = Form("Tamil Nadu"),
    district: str = Form(""),
    local_body: str = Form(""),
    nagaram_type: str = Form(""),
    constituency: str = Form(""),
    ward: str = Form(""),
    address: str = Form(""),
    voter_id: str = Form(""),
    aadhaar: str = Form(""),
    photo: UploadFile = File(None)
):
    # ---------- Duplicate check ----------
    if candidates_collection.find_one({"mobile": mobile}):
        raise HTTPException(status_code=400, detail="Mobile number already registered")
    membership_no = generate_membership_no()
    # ---------- Save Photo ----------
    photo_path = ""
    if photo:
        photo_ext = os.path.splitext(photo.filename)[1]
        photo_filename = f"{mobile}{photo_ext}"
        photo_path = os.path.join(UPLOAD_DIR, photo_filename)

        with open(photo_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

   

    # ---------- Mongo Document ----------
    candidate_doc = {
        "membership_no": membership_no,
        "name": name,
        "father_name": father_name,
        "gender": gender,
        "dob": dob,
        "age": age,
        "blood_group": blood_group,
        "mobile": mobile,
        "email": email,
        "state": state,
        "district": district,
        "local_body": local_body,
        "nagaram_type": nagaram_type,
        "constituency": constituency,
        "ward": ward,
        "address": address,
        "voter_id": voter_id,
        "aadhaar": aadhaar,
        "photo": f"/uploads/{photo_filename}" if photo else "",
              
    }

    result = candidates_collection.insert_one(candidate_doc)
   
    
    return {
        "message": "Registration successful",
        "membership_no": membership_no,
        
        "id": str(result.inserted_id)
    }

# ===================== ADMIN =====================
@app.get("/admin")
def get_all_candidates():
    candidates = list(
        candidates_collection.find(
            {},
            {
                "_id": 1,
                "name": 1,
                "mobile": 1,
                "district": 1,
                "gender": 1,
                "age": 1,
            }
        )
    )

    for c in candidates:
        c["_id"] = str(c["_id"])

    return candidates

# ===================== ID CARD PDF =====================
@app.get("/admin/idcard/{mobile}")
def generate_idcard(mobile: str):

    cnd = candidates.find_one({"mobile": mobile})
    if not cnd:
        raise HTTPException(status_code=404, detail="Member not found")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A7))
    width, height = landscape(A7)

    # Tamil Font (BUILT-IN – Render SAFE)
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

    party_dark = HexColor("#114D2B")
    party_light = HexColor("#1CF791")

    # ================= FRONT =================
    c.setFillColor(white)
    c.rect(0, 0, width, height, fill=1)

    # Curved design
    c.setFillColor(party_dark)
    c.roundRect(width - 30*mm, -10*mm, 40*mm, height + 20*mm, 40, fill=1)

    c.setFillColor(party_light)
    c.roundRect(width - 38*mm, -10*mm, 30*mm, height + 20*mm, 40, fill=1)

    # Party Name (Tamil)
    c.setFont("HeiseiMin-W3", 10)
    c.setFillColor(party_dark)
    c.drawString(8*mm, height - 12*mm, "பசுமை பாரத மக்கள் கட்சி")

    # Name
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(black)
    c.drawString(8*mm, height - 26*mm, cnd["name"].upper())

    c.line(8*mm, height - 29*mm, width - 45*mm, height - 29*mm)

    c.setFont("Helvetica", 7)
    c.drawString(8*mm, height - 38*mm, f"📞 {cnd['mobile']}")
    c.drawString(8*mm, height - 46*mm, f"📍 {cnd['district']}")
    c.drawString(8*mm, height - 54*mm, f"ID : {cnd['membership_no']}")

    # Photo
    if cnd.get("photo_path") and os.path.exists(cnd["photo_path"]):
        c.drawImage(
            cnd["photo_path"],
            width - 28*mm,
            height - 40*mm,
            20*mm,
            26*mm,
            mask="auto"
        )

    c.showPage()

    # ================= BACK =================
    c.setFillColor(white)
    c.rect(0, 0, width, height, fill=1)

    c.setFont("HeiseiMin-W3", 8)
    c.setFillColor(black)
    c.drawCentredString(width/2, height - 20*mm, "உறுப்பினர் விதிமுறைகள்")

    c.setFont("Helvetica", 6)
    c.drawCentredString(width/2, height - 32*mm, "Official identification only")
    c.drawCentredString(width/2, height - 40*mm, "If found please return")

    c.line(10*mm, 15*mm, 45*mm, 15*mm)
    c.drawString(10*mm, 10*mm, "Authorized Sign")

    c.circle(width - 20*mm, 15*mm, 8*mm)
    c.drawCentredString(width - 20*mm, 10*mm, "OFFICIAL")

    c.showPage()
    c.save()

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={mobile}_ID_CARD.pdf"
        }
    )
    
    
@app.get("/district-secretaries")
def get_district_secretaries():
    return [
        {
            "name": "திரு. மு. செந்தில்",
            "district": "சென்னை",
            "photo": "/assets/district_secretaries/dum.jpeg"
        },
        {
            "name": "திரு. க. ரமேஷ்",
            "district": "மதுரை",
            "photo": "/assets/district_secretaries/dum.jpeg"
        },
        {
            "name": "திருமதி. சு. லதா",
            "district": "கோயம்புத்தூர்",
            "photo": "/assets/district_secretaries/dum.jpeg"
        }
    ]
