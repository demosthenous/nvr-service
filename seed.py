import json
from pathlib import Path
from app import db, repository as repo
from app.models import NVR, Camera

def main():
    conn = db.get_connection()
    db.init_db(conn)
    data = json.loads(Path("sample_nvr_camera_data.json").read_text())
    for raw in data["nvrs"]:
        repo.create_nvr(conn, NVR(**raw))
    for raw in data["cameras"]:
        repo.create_camera(conn, Camera(**raw))
    conn.close()
    print("Seeded.")

if __name__ == "__main__":
    main()