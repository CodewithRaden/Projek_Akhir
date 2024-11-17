from flask import Flask, request, render_template, jsonify, session, redirect, url_for
import sqlite3
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = 'matherfaker' 
local_timezone = pytz.timezone('Asia/Jakarta')


@app.route('/')
def home():
     return render_template('home.html')


@app.route('/index')
def index():
    if 'admin_logged_in' in session and session['admin_logged_in']:
        return render_template('index.html', is_admin=True)
    return render_template('index.html', is_admin=False)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_username = request.form['username']
        admin_password = request.form['password']
        
        if admin_username == 'admin' and admin_password == 'password':
            session['admin_logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))


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
        message = 'User registered successfully!'
        status = 'success'
    except sqlite3.IntegrityError:
        message = 'Username or RFID tag already exists!'
        status = 'error'
    finally:
        conn.close()

    # Render the template and pass the message and status to the HTML
    return render_template('register.html', message=message, status=status)


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
        
        
@app.route('/view_users')
def view_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, rfid_tag FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('view_users.html', users=users)

@app.route('/view_lockers')
def view_lockers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT locker_number, status FROM lockers")
    lockers = cursor.fetchall()
    conn.close()
    return render_template('view_lockers.html', lockers=lockers)


@app.route('/monitoring', methods=['GET'])
def monitoring():
    user_filter = request.args.get('user')
    status_filter = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    locker_number_filter = request.args.get('locker_number')  # New locker number filter
    page = request.args.get('page', default=1, type=int)  # Current page, default is 1
    per_page = 8  # Max data per page

    # Base queries
    base_query = '''
    SELECT lockers.locker_number, users.username, users.rfid_tag, access_logs.access_time, access_logs.action
    FROM access_logs
    JOIN users ON access_logs.user_id = users.id
    JOIN lockers ON access_logs.locker_id = lockers.id
    WHERE 1=1
    '''

    count_query = '''
    SELECT COUNT(*)
    FROM access_logs
    JOIN users ON access_logs.user_id = users.id
    JOIN lockers ON access_logs.locker_id = lockers.id
    WHERE 1=1
    '''

    conditions = []
    params = []

    # Add filters if applicable
    if user_filter:
        conditions.append("users.username = ?")
        params.append(user_filter)
    
    if status_filter:
        if status_filter.lower() == 'open':
            conditions.append("access_logs.action = 'open'")
        elif status_filter.lower() == 'close':
            conditions.append("access_logs.action = 'close'")
    
    if start_date:
        conditions.append("access_logs.access_time >= ?")
        params.append(start_date + " 00:00:00")
    
    if end_date:
        conditions.append("access_logs.access_time <= ?")
        params.append(end_date + " 23:59:59")

    if locker_number_filter:
        conditions.append("lockers.locker_number = ?")
        params.append(locker_number_filter)

    if conditions:
        condition_str = " AND " + " AND ".join(conditions)
        base_query += condition_str
        count_query += condition_str

    # Add sorting and pagination
    base_query += " ORDER BY access_logs.access_time DESC LIMIT ? OFFSET ?"
    params_for_data_query = params + [per_page, (page - 1) * per_page]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Execute data query
    cursor.execute(base_query, params_for_data_query)
    records = cursor.fetchall()

    # Execute count query
    cursor.execute(count_query, params)
    total_records = cursor.fetchone()[0]

    conn.close()

    # Calculate total pages
    total_pages = (total_records + per_page - 1) // per_page

    # Format data for rendering
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

    return render_template('monitoring.html', 
                           monitoring_data=monitoring_data, 
                           page=page, 
                           total_pages=total_pages)



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
