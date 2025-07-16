import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# ⚠️ Löscht ALLE Schichten
cursor.execute('DELETE FROM shifts')
cursor.execute('DELETE FROM wishes')  # Optional: Auch alle Wünsche löschen

conn.commit()
conn.close()

print("Kalender (Schichten und Wünsche) zurückgesetzt.")
