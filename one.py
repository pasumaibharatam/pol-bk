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

