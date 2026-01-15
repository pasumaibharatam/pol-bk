from main import candidates_collection, generate_id_card, IDCARD_DIR
import os

def fix_old_candidates():
    for c in candidates_collection.find():
        mobile = str(c.get("mobile", "")).strip()

        candidates_collection.update_one(
            {"_id": c["_id"]},
            {"$set": {"mobile": mobile}}
        )

        pdf_path = f"{IDCARD_DIR}/{mobile}.pdf"
        if not os.path.exists(pdf_path):
            generate_id_card(c)

    print("✅ Old candidates fixed!")

fix_old_candidates()

@app.post("/admin/fix-membership")
def fix_membership_numbers():
    users = candidates_collection.find({"membership_no": {"$exists": False}})
    count = candidates_collection.count_documents({})

    for i, user in enumerate(users, start=1):
        membership_no = f"PBM-{datetime.now().year}-{count + i:06d}"
        candidates_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"membership_no": membership_no}}
        )

    return {"message": "Membership numbers updated"}