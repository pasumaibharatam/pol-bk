from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os
import urllib.parse
import shutil
import io
from fastapi.staticfiles import StaticFiles
from reportlab.lib.pagesizes import A6
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from fastapi.responses import StreamingResponse
import qrcode
# ===================== APP =====================
app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

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
IDCARD_DIR = "idcards"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(IDCARD_DIR, exist_ok=True)

# ===================== DATABASE =====================
USERNAME = "pasumaibharatam_db_user"
PASSWORD = urllib.parse.quote_plus("pasumai123")
CLUSTER = "pasumai.mrsonfr.mongodb.net"

MONGO_URL = f"mongodb+srv://{USERNAME}:{PASSWORD}@{CLUSTER}/?retryWrites=true&w=majority"

client = MongoClient(MONGO_URL)
db = client["political_db"]
candidates_collection = db["candidates"]



# ===================== DISTRICTS =====================
@app.get("/districts")
def get_districts():
    districts = list(db.districts.find({}, {"_id": 0, "name": 1}))
    return [d["name"] for d in districts]

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
def generate_membership_no():
    count = candidates_collection.count_documents({})
    return f"PBM-{datetime.now().year}-{count + 1:06d}"


# ===================== DOWNLOAD ID CARD (REGENERATE PDF) =====================
from reportlab.lib.pagesizes import A7, landscape
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from fastapi.responses import StreamingResponse
import io, os

@app.get("/admin/idcard/{mobile}")
def download_idcard(mobile: str):

    cnd = candidates_collection.find_one({"mobile": mobile})
    if not cnd:
        raise HTTPException(status_code=404, detail="ID card not found")

    member_id = cnd.get("membership_no", "PBM-XXXX")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A7))
    width, height = landscape(A7)

    # Tamil font
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

    # Party colours
    party_dark = HexColor("#0F7A3E")
    party_light = HexColor("#5FB48C")

    # ================= FRONT =================

    # Background
    c.setFillColor(white)
    c.rect(0, 0, width, height, fill=1)

    # Right curved wave
    c.setFillColor(party_dark)
    c.roundRect(width - 30*mm, -10*mm, 40*mm, height + 20*mm, 40, fill=1)

    c.setFillColor(party_light)
    c.roundRect(width - 38*mm, -10*mm, 30*mm, height + 20*mm, 40, fill=1)

    # Party Name (Tamil)
    c.setFillColor(party_dark)
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(8*mm, height - 12*mm, "பசுமை பாரத மக்கள் கட்சி")

    # Member Name (BIG)
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(black)
    c.drawString(8*mm, height - 26*mm, cnd["name"].upper())

    # Divider
    c.setLineWidth(0.5)
    c.line(8*mm, height - 29*mm, width - 45*mm, height - 29*mm)

    # Details
    c.setFont("Helvetica", 7)
    c.drawString(8*mm, height - 38*mm, f"📞 {cnd['mobile']}")
    c.drawString(8*mm, height - 46*mm, f"📍 {cnd['district']}")
    c.drawString(8*mm, height - 54*mm, f"ID : {member_id}")

    # Photo (optional)
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

    # Background
    c.setFillColor(white)
    c.rect(0, 0, width, height, fill=1)

    # Rules
    c.setFillColor(black)
    c.setFont("HeiseiMin-W3", 8)
    c.drawCentredString(width/2, height - 20*mm, "உறுப்பினர் விதிமுறைகள்")

    c.setFont("Helvetica", 6)
    c.drawCentredString(width/2, height - 30*mm, "This card is for official identification only")
    c.drawCentredString(width/2, height - 38*mm, "If found, please return to party office")

    # Signature
    c.line(10*mm, 15*mm, 45*mm, 15*mm)
    c.drawString(10*mm, 10*mm, "Authorized Signature")

    # Seal text
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

@app.get("/verify/{member_id}")
def verify_member(member_id: str):
    member = candidates_collection.find_one({"membership_no": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Invalid Member")

    return {
        "status": "Valid Member",
        "name": member["name"],
        "mobile": member["mobile"],
        "district": member["district"],
        "membership_no": member["membership_no"]
    }

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


