import psycopg

try:
    conn = psycopg.connect('postgresql://postgres:Abcd%401234@127.0.0.1:5432/notebook')
    with conn.cursor() as cur:
        cur.execute("UPDATE equipment_resources SET status = 'active';")
        conn.commit()
    print("Database equipment status updated to 'active'")
except Exception as e:
    print("DB error:", e)
