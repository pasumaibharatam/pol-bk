from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pymongo import MongoClient
from datetime import datetime
import os, io, shutil, urllib.parse

# ===================== REPORTLAB =====================
from reportlab.lib.pagesizes import A7, landscape
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ===================== APP =====================
app = FastAPI()

pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

# ===================== CORS =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://pasumaibharatam.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== DIRECTORIES =====================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

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

# ===================== MEMBERSHIP NO =====================
def generate_membership_no():
    count = candidates_collection.count_documents({})
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
    if candidates_collection.find_one({"mobile": mobile}):
        raise HTTPException(status_code=400, detail="Mobile number already registered")

    membership_no = generate_membership_no()

    # ---------- Save photo (ONLY filename in DB) ----------
    photo_filename = None
    
    if photo and photo.filename:
        _, photo_ext = os.path.splitext(photo.filename)   # <-- THIS LINE CREATES photo_ext
    
        # fallback if extension missing
        if not photo_ext:
            photo_ext = ".jpg"
    
        photo_filename = f"{mobile}{photo_ext}"
        photo_path = os.path.join(UPLOAD_DIR, photo_filename)
    
        with open(photo_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)



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
        "photo": photo_filename,   # ✅ ONLY filename
    }

    result = candidates_collection.insert_one(candidate_doc)

    return {
        "message": "Registration successful",
        "membership_no": membership_no,
        "id": str(result.inserted_id)
    }

# ===================== ADMIN LIST =====================
@app.get("/admin")
def get_all_candidates():
    candidates = list(
        candidates_collection.find(
            {},
            {"_id": 1, "name": 1, "mobile": 1, "district": 1, "gender": 1, "age": 1}
        )
    )

    for c in candidates:
        c["_id"] = str(c["_id"])

    return candidates

# ===================== ID CARD PDF =====================
@app.get("/admin/idcard/{mobile}")
def generate_idcard(mobile: str):
    cnd = candidates_collection.find_one({"mobile": mobile})
    if not cnd:
        raise HTTPException(status_code=404, detail="Member not found")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A7))
    width, height = landscape(A7)

    bar_width = 10 * mm

    # Background
    c.setFillColor(HexColor("#1B5E20"))
    c.rect(0, 0, bar_width, height, fill=1, stroke=0)
    c.rect(width - bar_width, 0, bar_width, height, fill=1, stroke=0)

    c.setFillColor(HexColor("#E8F5E9"))
    c.rect(bar_width, 0, width - 2 * bar_width, height, fill=1, stroke=0)

    # Party name
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(HexColor("#1B5E20"))
    c.drawCentredString(width / 2, height - 10 * mm, "PASUMAI BHARAT MAKKAL KATCHI")

    # Photo
    photo_radius = 15 * mm
    photo_x = bar_width + 20 * mm
    photo_y = height / 2

    photo_filename = cnd.get("photo")

    if photo_filename:
        abs_photo_path = os.path.join(UPLOAD_DIR, photo_filename)

        print("PHOTO PATH:", abs_photo_path)

        if os.path.exists(abs_photo_path):
            c.drawImage(
                abs_photo_path,
                photo_x - photo_radius,
                photo_y - photo_radius,
                2 * photo_radius,
                2 * photo_radius,
                preserveAspectRatio=True,
                mask="auto",
            )
        else:
            print("❌ PHOTO NOT FOUND")
    else:
        print("❌ PHOTO FIELD EMPTY")

    # draw border last
    c.setStrokeColor(HexColor("#1B5E20"))
    c.setLineWidth(1)
    c.circle(photo_x, photo_y, photo_radius, fill=0)

    # Text
    c.setFont("Helvetica-Bold", 9)
    tx = photo_x + photo_radius + 7 * mm
    ty = photo_y + 15 * mm
    gap = 12

    c.drawString(tx, ty, cnd["name"].upper())
    c.drawString(tx, ty - gap, f"Mobile: {cnd['mobile']}")
    c.drawString(tx, ty - 2 * gap, f"District: {cnd['district']}")
    c.drawString(tx, ty - 3 * gap, f"ID: {cnd['membership_no']}")

    c.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=idcard.pdf"},
    )

# ===================== DISTRICT SECRETARIES =====================
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
