import sqlite3
try:
    conn = sqlite3.connect("users.db")
    conn.execute("SELECT 1")
    print("✅ Datenbank ist erreichbar.")
except sqlite3.OperationalError as e:
    print("⚠️ Fehler:", e)
finally:
    conn.close()
