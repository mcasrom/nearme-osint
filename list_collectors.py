from src.db import get_conn

conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT DISTINCT collector FROM collector_runs ORDER BY collector")
print("todos los colectores en BD:")
for r in cur.fetchall():
    print("  -", r[0])
conn.close()
