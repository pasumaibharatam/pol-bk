from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
import urllib.parse
import shutil
from reportlab.lib.pagesizes import A6
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode
from fastapi.responses import FileResponse
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

# ===================== STATIC FILES =====================
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/idcards", StaticFiles(directory=IDCARD_DIR), name="idcards")

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

    # ---------- Create ID Card File (placeholder) ----------
    idcard_filename = f"{mobile}.txt"
    idcard_path = os.path.join(IDCARD_DIR, idcard_filename)

    with open(idcard_path, "w", encoding="utf-8") as f:
        f.write(f"""
ID CARD
-------
Name      : {name}
Mobile    : {mobile}
District  : {district}
Constituency : {constituency}
        """)

    # ---------- Mongo Document ----------
    candidate_doc = {
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
        "idcard": f"/idcards/{idcard_filename}",
        "created_at": datetime.utcnow()
    }

    result = candidates_collection.insert_one(candidate_doc)
    pdf_url = create_id_card_pdf(candidate_doc)
    candidates_collection.update_one(
        {"_id": result.inserted_id},
        {"$set": {"idcard": pdf_url}}
    )
    return {
        "message": "Registration successful",
        "membership_no": membership_no,
        "idcard": pdf_url,
        "id": str(result.inserted_id)
    }
def generate_membership_no():
    count = candidates_collection.count_documents({})
    return f"PBM-{datetime.now().year}-{count + 1:06d}"
def create_id_card_pdf(candidate):
    pdf_path = os.path.join(IDCARD_DIR, f"{candidate['mobile']}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=A6)
    width, height = A6

    # Header
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 20, "பசுமை பாரத மக்கள் கட்சி")

    # Photo
    if candidate["photo"]:
        photo_path = candidate["photo"].replace("/uploads/", "uploads/")
        c.drawImage(photo_path, 10, height - 90, 60, 70)

    # Details
    c.setFont("Helvetica", 9)
    c.drawString(80, height - 40, f"Name : {candidate['name']}")
    c.drawString(80, height - 55, f"Mobile : {candidate['mobile']}")
    c.drawString(80, height - 70, f"District : {candidate['district']}")
    c.drawString(80, height - 85, f"Member ID : {candidate['membership_no']}")

    # QR Code
    qr_data = f"""
Name: {candidate['name']}
Mobile: {candidate['mobile']}
Member ID: {candidate['membership_no']}
"""
    qr = qrcode.make(qr_data)
    qr_path = f"temp_qr_{candidate['mobile']}.png"
    qr.save(qr_path)

    c.drawImage(qr_path, width - 70, 20, 50, 50)
    os.remove(qr_path)

    c.showPage()
    c.save()

    return f"/idcards/{candidate['mobile']}.pdf"
@app.get("/admin/idcard/{mobile}")
def download_idcard(mobile: str):
    pdf_path = os.path.join(IDCARD_DIR, f"{mobile}.pdf")

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="ID card not found")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{mobile}_ID_CARD.pdf"
    )