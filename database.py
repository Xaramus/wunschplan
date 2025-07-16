import sqlite3

def create_tables():
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    # Benutzer-Tabelle
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Schichten-Tabelle
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            shift_type TEXT NOT NULL  -- z. B. Früh, Spät, Nacht
        )
    ''')

    # Wunsch-Tabelle
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            shift_id INTEGER,
            status TEXT DEFAULT 'offen',  -- offen, akzeptiert, abgelehnt
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(shift_id) REFERENCES shifts(id)
        )
    ''')

    connection.commit()
    connection.close()


def insert_sample_shifts():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    shifts = [
        ('2025-07-20', 'Früh'),
        ('2025-07-20', 'Spät'),
        ('2025-07-21', 'Nacht'),
        ('2025-07-21', 'Früh'),
        ('2025-07-22', 'Spät')
    ]

    # Nur einfügen, wenn noch keine vorhanden sind
    existing = cursor.execute('SELECT COUNT(*) FROM shifts').fetchone()[0]
    if existing == 0:
        cursor.executemany('INSERT INTO shifts (date, shift_type) VALUES (?, ?)', shifts)

    conn.commit()
    conn.close()


# ✅ Gemeinsamer Startblock
if __name__ == '__main__':
    create_tables()
    insert_sample_shifts()
