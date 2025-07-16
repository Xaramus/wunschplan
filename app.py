from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = 'geheim'  # Für Sessions

# Datenbankverbindung
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return 'E-Mail bereits registriert.'
        finally:
            conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        else:
            return 'Login fehlgeschlagen.'

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT name, is_admin FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()

    return render_template('dashboard.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/shifts')
def show_shifts():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    shifts = conn.execute('SELECT * FROM shifts').fetchall()
    conn.close()

    return render_template('shifts.html', shifts=shifts)


@app.route('/wish/<int:shift_id>', methods=['POST'])
def wish_shift(shift_id):
    if 'user_id' not in session:
        return redirect(url_for('show_shifts'))

    user_id = session['user_id']

    conn = get_db_connection()

    # Duplikate verhindern
    existing = conn.execute('SELECT * FROM wishes WHERE user_id = ? AND shift_id = ?', (user_id, shift_id)).fetchone()
    if existing:
        conn.close()
        return 'Du hast dich bereits für diese Schicht beworben.'

    conn.execute('INSERT INTO wishes (user_id, shift_id) VALUES (?, ?)', (user_id, shift_id))
    conn.commit()
    conn.close()

    return redirect(url_for('shifts'))

from calendar import monthrange
from datetime import date, datetime

@app.route('/kalender')
def kalender():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    monat = int(request.args.get('monat', datetime.today().month))
    jahr = int(request.args.get('jahr', datetime.today().year))
    _, tage_im_monat = monthrange(jahr, monat)
    tage = [date(jahr, monat, tag) for tag in range(1, tage_im_monat + 1)]

    conn = get_db_connection()
    user_id = session['user_id']

    # ✅ Alle Tage, für die sich der User beworben hat
    belegt_tage_raw = conn.execute('''
        SELECT DISTINCT s.date
        FROM wishes w
        JOIN shifts s ON w.shift_id = s.id
        WHERE w.user_id = ?
    ''', (user_id,)).fetchall()
    conn.close()

    # Liste mit belegten Datumswerten als Strings
    belegt_tage = set([row['date'] for row in belegt_tage_raw])

    return render_template('kalender.html', tage=tage, monat=monat, jahr=jahr, belegt_tage=belegt_tage)

@app.route('/shifts/<datum>', methods=['GET', 'POST'])
def show_shifts_for_day(datum):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    # ✅ Schritt 1: Prüfen, ob für diesen Tag schon Schichten existieren
    existing_shifts = conn.execute(
        'SELECT COUNT(*) FROM shifts WHERE date = ?', (datum,)
    ).fetchone()[0]

    # ✅ Schritt 2: Falls nicht, automatisch Standard-Schichten anlegen
    if existing_shifts == 0:
        default_shifts = ['SL', 'ZB1', 'B1', 'CTZ 1', 'CTZ 2', 'Frei']
        for shift_type in default_shifts:
            conn.execute(
                'INSERT INTO shifts (date, shift_type) VALUES (?, ?)', (datum, shift_type)
            )
        conn.commit()

    # ✅ Wunsch absenden
    if request.method == 'POST':
        # Prüfen, ob der Benutzer für diesen Tag schon eine Schicht gewählt hat
        existing_wish = conn.execute('''
            SELECT s.id AS shift_id
            FROM wishes w
            JOIN shifts s ON w.shift_id = s.id
            WHERE w.user_id = ? AND s.date = ?
        ''', (user_id, datum)).fetchone()

        if not existing_wish:
            selected_shift_ids = request.form.getlist('shift_ids')
            if selected_shift_ids:
                shift_id = selected_shift_ids[0]  # Nur den ersten Eintrag akzeptieren
                conn.execute('INSERT INTO wishes (user_id, shift_id) VALUES (?, ?)', (user_id, shift_id))
            conn.commit()

    # ✅ Alle Schichten (inkl. Wunschstatus) laden
    shifts = conn.execute('''
        SELECT s.*, 
               (SELECT 1 FROM wishes w WHERE w.user_id = ? AND w.shift_id = s.id) AS wished
        FROM shifts s
        WHERE s.date = ?
    ''', (user_id, datum)).fetchall()

    conn.close()

    return render_template('schicht_tag.html', datum=datum, shifts=shifts)



from datetime import datetime

@app.route('/my_wishes')
def my_wishes():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Monat/Jahr aus URL oder Standard = heute
    monat = int(request.args.get('monat', datetime.today().month))
    jahr = int(request.args.get('jahr', datetime.today().year))

    conn = get_db_connection()

    wishes = conn.execute('''
        SELECT s.date, s.shift_type, w.status
        FROM wishes w
        JOIN shifts s ON w.shift_id = s.id
        WHERE w.user_id = ?
          AND strftime('%m', s.date) = ?
          AND strftime('%Y', s.date) = ?
        ORDER BY s.date
    ''', (user_id, f"{monat:02}", str(jahr))).fetchall()

    conn.close()

    return render_template('my_wishes.html', wishes=wishes, monat=monat, jahr=jahr)


@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if not user['is_admin']:
        conn.close()
        return 'Zugriff verweigert.'

    # Alle offenen Wünsche laden
    wishes = conn.execute('''
        SELECT w.id, u.name AS user_name, s.date, s.shift_type, w.status
        FROM wishes w
        JOIN users u ON w.user_id = u.id
        JOIN shifts s ON w.shift_id = s.id
        WHERE w.status = 'offen'
        ORDER BY s.date
    ''').fetchall()
    conn.close()

    return render_template('admin_dashboard.html', wishes=wishes)

@app.route('/admin/wish/<int:wish_id>/<action>')
def handle_wish(wish_id, action):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if not user['is_admin']:
        conn.close()
        return 'Zugriff verweigert.'

    if action in ['akzeptieren', 'ablehnen']:
        new_status = 'akzeptiert' if action == 'akzeptieren' else 'abgelehnt'
        conn.execute('UPDATE wishes SET status = ? WHERE id = ?', (new_status, wish_id))
        conn.commit()

    conn.close()
    return redirect(url_for('admin_dashboard'))



if __name__ == '__main__':
    app.run()
