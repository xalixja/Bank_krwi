import psycopg2

def get_db():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="123qwe",
        host="localhost",
        port=5432,
        options="-c search_path=bank_krwi"
    )

conn = get_db()
cur = conn.cursor()

cur.close()
conn.close()
