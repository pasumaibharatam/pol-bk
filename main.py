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

pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
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
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

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
    cnd = candidates_collection.find_one({"mobile": mobile})
    if not cnd:
        raise HTTPException(status_code=404, detail="Member not found")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A7))
    width, height = landscape(A7)

    # Bars and background
    bar_width = 10*mm
    c.setFillColor(HexColor('#388E3C'))
    c.rect(0, 0, bar_width, height, fill=1, stroke=0)
    c.rect(width-bar_width, 0, bar_width, height, fill=1, stroke=0)
    c.setFillColor(HexColor('#C8E6C9'))
    c.rect(bar_width, 0, width-2*bar_width, height, fill=1, stroke=0)

    # Party Name
    c.setFont("HeiseiMin-W3", 14)
    c.setFillColor(HexColor('#1B5E20'))
    c.drawCentredString(width/2, height-10*mm, "பசுமை பாரத மக்கள் கட்சி")

    # Photo placeholder
    photo_radius = 15*mm
    photo_center_x = bar_width + 20*mm
    photo_center_y = height/2
    c.setFillColor(HexColor('#FFFFFF'))
    c.circle(photo_center_x, photo_center_y, photo_radius, fill=1)
    c.setLineWidth(1)
    c.setStrokeColor(HexColor('#1B5E20'))
    c.circle(photo_center_x, photo_center_y, photo_radius, fill=0)

    # Insert real photo if available
    photo_path = cnd.get("photo")
    if photo_path:
     real_path = os.path.join(os.getcwd(), photo_path.lstrip("/"))
     if os.path.exists(real_path):
        c.drawImage(
            real_path,
            photo_center_x - photo_radius,
            photo_center_y - photo_radius,
            2*photo_radius,
            2*photo_radius,
            mask='auto'
        )


    # Member info
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(HexColor('#000000'))
    text_start_x = photo_center_x + photo_radius + 7*mm
    text_start_y = photo_center_y + 15*mm
    line_spacing = 10
    c.drawString(text_start_x, text_start_y, cnd["name"].upper())
    c.drawString(text_start_x, text_start_y - line_spacing, f"📞  {cnd['mobile']}")
    c.drawString(text_start_x, text_start_y - 2*line_spacing, f"📍  {cnd['district']}")
    c.drawString(text_start_x, text_start_y - 3*line_spacing, f"ID: {cnd['membership_no']}")

    # Bottom line
    c.setStrokeColor(HexColor('#1B5E20'))
    c.setLineWidth(1)
    c.line(bar_width, 5*mm, width-bar_width, 5*mm)

    # Back page
    c.showPage()
    c.setFillColor(HexColor('#388E3C'))
    c.rect(0, 0, bar_width, height, fill=1, stroke=0)
    c.rect(width-bar_width, 0, bar_width, height, fill=1, stroke=0)
    c.setFillColor(HexColor('#E8F5E9'))
    c.rect(bar_width, 0, width-2*bar_width, height, fill=1, stroke=0)
    c.setFont("HeiseiMin-W3", 10)
    c.setFillColor(HexColor('#1B5E20'))
    c.drawCentredString(width/2, height-15*mm, "சுற்றுச்சூழல் • சமத்துவம் • சமூக நீதி")
    c.setFont("Helvetica", 7)
    c.drawCentredString(width/2, 5*mm, "Website: www.pasumaiparty.in | Contact: 9876598765") 

    # Save and return
    c.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename={cnd['membership_no']}.pdf"
    })

    
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
