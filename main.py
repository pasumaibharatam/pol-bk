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
    age: int = Form(...),
    blood_group: str = Form(...),
    mobile: str = Form(...),
    district: str = Form(...),
    photo: UploadFile = File(None)
):
    if candidates.find_one({"mobile": mobile}):
        raise HTTPException(status_code=400, detail="Mobile already registered")

    photo_path = ""
    if photo:
        ext = os.path.splitext(photo.filename)[1]
        filename = f"{mobile}{ext}"
        photo_path = os.path.join(UPLOAD_DIR, filename)
        with open(photo_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

    doc = {
        "membership_no": generate_membership_no(),
        "name": name,
        "age": age,
        "blood_group": blood_group,
        "mobile": mobile,
        "district": district,
        "photo_path": photo_path
    }

    candidates.insert_one(doc)

    return {"message": "Registered successfully"}

# ===================== ADMIN =====================
@app.get("/admin")
def admin_list():
    data = []
    for c in candidates.find({}, {"_id": 0}):
        data.append(c)
    return data

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

    party_dark = HexColor("#0F7A3E")
    party_light = HexColor("#5FB48C")

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
