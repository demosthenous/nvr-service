from app import db
from app.seeding import seed_sample_data


def main():
    conn = db.get_connection()
    db.init_db(conn)
    seed_sample_data(conn)
    conn.close()
    print("Seeded.")


if __name__ == "__main__":
    main()
