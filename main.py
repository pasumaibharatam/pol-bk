from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os
import urllib.parse
import shutil
import io

from reportlab.lib.pagesizes import A6
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from fastapi.responses import StreamingResponse
import qrcode
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
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode, io, os

@app.get("/admin/idcard/{mobile}")
def download_idcard(mobile: str):

    cnd = candidates_collection.find_one({"mobile": mobile})
    if not cnd:
        raise HTTPException(status_code=404, detail="ID card not found")

    member_id = cnd.get("membership_no", "PBM-XXXX")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A7))
    width, height = landscape(A7)

    # ================= FRONT SIDE =================
    # Watermark Logo
    logo = "assets/party_logo.png"
    if os.path.exists(logo):
        c.saveState()
        c.setFillAlpha(0.08)
        c.drawImage(logo, width/2 - 20*mm, height/2 - 20*mm, 40*mm, 40*mm)
        c.restoreState()

    # Header
    c.setFillColor(HexColor("#0F7A3E"))
    c.rect(0, height - 14*mm, width, 14*mm, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width/2, height - 10*mm, "பசுமை பாரத மக்கள் கட்சி")
    c.setFont("Helvetica", 6)
    c.drawCentredString(width/2, height - 14.5*mm, "PASUMAI BHARAT PEOPLE'S PARTY")

    # Photo
    if cnd.get("photo_path") and os.path.exists(cnd["photo_path"]):
        c.drawImage(cnd["photo_path"], 5*mm, height-42*mm, 22*mm, 28*mm)

    # Details (Bilingual)
    c.setFillColor(HexColor("#000"))
    c.setFont("Helvetica", 6)
    c.drawString(32*mm, height-24*mm, f"பெயர் / Name : {cnd['name']}")
    c.drawString(32*mm, height-32*mm, f"மொபைல் / Mobile : {cnd['mobile']}")
    c.drawString(32*mm, height-40*mm, f"உறுப்பினர் எண் / ID : {member_id}")

    # QR Code
    verify_url = f"https://yourdomain.com/verify/{member_id}"
    qr = qrcode.make(verify_url)
    qr_buf = io.BytesIO()
    qr.save(qr_buf)
    qr_buf.seek(0)

    c.drawImage(ImageReader(qr_buf), width-25*mm, 5*mm, 20*mm, 20*mm)

    c.showPage()

    # ================= BACK SIDE =================
    # Watermark
    if os.path.exists(logo):
        c.saveState()
        c.setFillAlpha(0.05)
        c.drawImage(logo, width/2 - 25*mm, height/2 - 25*mm, 50*mm, 50*mm)
        c.restoreState()

    # Text
    c.setFont("Helvetica", 6)
    c.setFillColor(HexColor("#000"))
    c.drawCentredString(width/2, height-15*mm, "உறுப்பினர் விதிமுறைகள்")
    c.drawCentredString(width/2, height-22*mm, "This card is the property of PBM Party")
    c.drawCentredString(width/2, height-30*mm, "If found, please return to party office")

    # Signature
    c.line(10*mm, 15*mm, 40*mm, 15*mm)
    c.drawString(10*mm, 10*mm, "Authorized Signature")

    # Seal
    c.circle(width-20*mm, 15*mm, 8*mm)
    c.drawCentredString(width-20*mm, 10*mm, "OFFICIAL SEAL")

    c.showPage()
    c.save()

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={mobile}_ID_CARD.pdf"}
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


