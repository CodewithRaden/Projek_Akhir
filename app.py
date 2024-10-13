from flask import Flask, request, render_template, jsonify
import sqlite3
from datetime import datetime
import pytz

app = Flask(__name__)
local_timezone = pytz.timezone('Asia/Jakarta')

# Route untuk halaman indeks
@app.route('/')
def index():
    return render_template('index.html')

# Koneksi ke database
def get_db_connection():
    conn = sqlite3.connect('smart_locker.db')
    conn.row_factory = sqlite3.Row
    return conn

# Endpoint untuk mencatat akses
@app.route('/access', methods=['POST'])
def log_access():
    user_id = request.json['user_id']
    locker_id = request.json['locker_id']
    action = request.json['action']  # action should be 'open' or 'close'

    # Get the current local time
    access_time = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO access_logs (user_id, locker_id, access_time, action) VALUES (?, ?, ?, ?)',
                   (user_id, locker_id, access_time, action))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Access logged successfully!'}), 201

@app.route('/register', methods=['GET'])
def show_register():
    return render_template('register.html')

# Route untuk menangani pengiriman data registrasi
@app.route('/register', methods=['POST'])
def register_user():
    username = request.form['username']
    pin = request.form['pin']
    rfid_tag = request.form['rfid_tag']

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, pin, rfid_tag) VALUES (?, ?, ?)', 
                       (username, pin, rfid_tag))
        conn.commit()
        return jsonify({'message': 'User registered successfully!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or RFID tag already exists!'}), 400
    finally:
        conn.close()

def is_valid_rfid(rfid_tag):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE rfid_tag = ?", (rfid_tag,))
    user = cursor.fetchone()
    conn.close()
    return user is not None

@app.route('/rfid', methods=['POST'])
def rfid_access():
    rfid_tag = request.form.get('rfid')
    if not rfid_tag:
        return jsonify({"status": "error", "message": "No RFID provided"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        conn.execute("BEGIN IMMEDIATE;")

        cursor.execute("SELECT * FROM users WHERE rfid_tag = ?", (rfid_tag,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"status": "error", "message": "RFID not recognized"}), 403

        user_id = user['id']
        cursor.execute("SELECT * FROM lockers WHERE (status = 'available') OR (status = 'occupied' AND user_id = ?)", (user_id,))
        locker = cursor.fetchone()

        if locker:
            locker_id = locker['id']
            locker_number = locker['locker_number']

            # Get the current local time
            access_time = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')

            if locker['status'] == 'available':
                cursor.execute('UPDATE lockers SET status = ?, user_id = ? WHERE id = ?', ('occupied', user_id, locker_id))
                cursor.execute('INSERT INTO access_logs (user_id, locker_id, access_time, action) VALUES (?, ?, ?, ?)', (user_id, locker_id, access_time, 'open'))
                message = f"Locker {locker_number} is now occupied by you"

            elif locker['status'] == 'occupied' and locker['user_id'] == user_id:
                cursor.execute('UPDATE lockers SET status = ?, user_id = NULL WHERE id = ?', ('available', locker_id))
                cursor.execute('INSERT INTO access_logs (user_id, locker_id, access_time, action) VALUES (?, ?, ?, ?)', (user_id, locker_id, access_time, 'close'))
                message = f"Locker {locker_number} is now available"

            conn.commit()
            return jsonify({"status": "success", "message": message})

        else:
            return jsonify({"status": "error", "message": "Locker is currently occupied by another user"}), 403
    
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    
    finally:
        conn.close()



@app.route('/monitoring', methods=['GET'])
def monitoring():
    user_filter = request.args.get('user')
    locker_filter = request.args.get('locker')

    query = '''
    SELECT lockers.locker_number, users.username, users.rfid_tag, access_logs.access_time, access_logs.action
    FROM access_logs
    JOIN users ON access_logs.user_id = users.id
    JOIN lockers ON access_logs.locker_id = lockers.id
    WHERE 1=1
    '''
    params = []

    if user_filter:
        query += " AND users.username = ?"
        params.append(user_filter)
    
    if locker_filter:
        query += " AND lockers.locker_number = ?"
        params.append(locker_filter)

    query += " ORDER BY access_logs.access_time DESC"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()

    if not records:
        return "No data available", 404

    monitoring_data = []
    for record in records:
        locker_number, username, rfid_tag, access_time, action = record
        monitoring_data.append({
            'locker_number': locker_number,
            'username': username,
            'rfid_tag': rfid_tag,
            'access_time': access_time,
            'action': action
        })

    return render_template('monitoring.html', monitoring_data=monitoring_data)


# Endpoint untuk menambahkan loker
@app.route('/add_locker', methods=['GET', 'POST'])
def add_locker():
    if request.method == 'POST':
        locker_number = request.form['locker_number']  # Mengambil input nomor loker dari form

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO lockers (locker_number) VALUES (?)', (locker_number,))
            conn.commit()
            message = 'Locker added successfully!'
        except sqlite3.IntegrityError:
            message = 'Locker number already exists!'  # Jika nomor loker sudah ada
        finally:
            conn.close()

        return render_template('add_locker.html', message=message)

    return render_template('add_locker.html')  # Menampilkan form untuk menambahkan loker

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
