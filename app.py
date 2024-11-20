from flask import Flask, request, render_template, jsonify, session, redirect, url_for, flash
from supabase import create_client, Client
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = 'matherfaker' 
local_timezone = pytz.timezone('Asia/Jakarta')

url = "https://edgipgqjsitghqlahajs.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVkZ2lwZ3Fqc2l0Z2hxbGFoYWpzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE4OTQ5MTAsImV4cCI6MjA0NzQ3MDkxMH0.yfbZ8vHOnqwkRfHbV4XzimCax9yjzyph8aGp1bb-GoE"
supabase: Client = create_client(url, key)


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
    return supabase

# Endpoint untuk mencatat akses
@app.route('/access', methods=['POST'])
def log_access():
    user_id = request.json['user_id']
    locker_id = request.json['locker_id']
    action = request.json['action']  # action should be 'open' or 'close'

    # Get the current local time
    access_time = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')

    data = {
        "user_id": user_id,
        "locker_id": locker_id,
        "access_time": access_time,
        "action": action
    }

    # Insert into Supabase database
    response = supabase.table('access_logs').insert(data).execute()

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

    data = {
        "username": username,
        "pin": pin,
        "rfid_tag": rfid_tag
    }

    # Insert into Supabase database
    try:
        response = supabase.table('users').insert(data).execute()
        message = 'User registered successfully!'
        status = 'success'
    except Exception as e:
        message = f'Error: {e}'
        status = 'error'

    return render_template('register.html', message=message, status=status)


def is_valid_rfid(rfid_tag):
    response = supabase.table('users').select("*").eq('rfid_tag', rfid_tag).execute()
    return len(response.data) > 0

@app.route('/rfid', methods=['POST'])
def rfid_access():
    rfid_tag = request.form.get('rfid')
    if not rfid_tag:
        return jsonify({"status": "error", "message": "No RFID provided"}), 400

    # Validate RFID tag
    user_response = supabase.table('users').select("*").eq('rfid_tag', rfid_tag).execute()
    if not user_response.data:
        return jsonify({"status": "error", "message": "RFID not recognized"}), 403

    user = user_response.data[0]
    user_id = user['id']
    print(f"RFID Tag: {rfid_tag}, User ID: {user_id}")

    # Get current local time for logging
    access_time = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')

    # Check if user already has an assigned locker
    assigned_locker_response = supabase.table('lockers').select("*").eq('user_id', user_id).eq('status', 'occupied').execute()
    assigned_locker = assigned_locker_response.data[0] if assigned_locker_response.data else None

    if assigned_locker:
        # User is releasing an occupied locker
        locker_id = assigned_locker['id']
        locker_number = assigned_locker['locker_number']

        # Update locker status and log the action
        supabase.table('lockers').update({
            "status": "available",
            "user_id": None
        }).eq('id', locker_id).execute()

        supabase.table('access_logs').insert({
            "user_id": user_id,
            "locker_id": locker_id,
            "access_time": access_time,
            "action": "close"
        }).execute()

        return jsonify({"status": "success", "message": f"Locker {locker_number} is now available"})

    else:
        # Try to assign a new locker if available
        available_locker_response = supabase.table('lockers').select("*").eq('status', 'available').limit(1).execute()
        if available_locker_response.data:
            available_locker = available_locker_response.data[0]
            locker_id = available_locker['id']
            locker_number = available_locker['locker_number']

            # Update locker status and log the action
            supabase.table('lockers').update({
                "status": "occupied",
                "user_id": user_id
            }).eq('id', locker_id).execute()

            supabase.table('access_logs').insert({
                "user_id": user_id,
                "locker_id": locker_id,
                "access_time": access_time,
                "action": "open"
            }).execute()

            return jsonify({"status": "success", "message": f"Locker {locker_number} is now assigned to you"})

        else:
            # No lockers are available
            return jsonify({"status": "error", "message": "Locker is currently occupied by another user"}), 403


        
@app.route('/pin_access', methods=['POST'])
def pin_access():
    pin = request.form.get('pin')
    if not pin:
        return jsonify({"status": "error", "message": "No PIN provided"}), 400

    try:
        # Validate PIN and fetch user details
        user_response = supabase.table('users').select('*').eq('pin', pin).execute()
        if not user_response.data:
            return jsonify({"status": "error", "message": "PIN not recognized"}), 403

        user = user_response.data[0]
        user_id = user['id']
        print(f"PIN: {pin}, User ID: {user_id}")

        # Check for a locker assigned to the user
        locker_response = supabase.table('lockers').select('*').eq('user_id', user_id).execute()
        locker = locker_response.data[0] if locker_response.data else None

        # Get the current local time for access logs
        access_time = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')

        if locker:
            locker_id = locker['id']
            locker_number = locker['locker_number']

            if locker['status'] == 'available':
                # Occupy the locker
                supabase.table('lockers').update({
                    'status': 'occupied',
                    'user_id': user_id
                }).eq('id', locker_id).execute()

                # Log the access
                supabase.table('access_logs').insert({
                    'user_id': user_id,
                    'locker_id': locker_id,
                    'access_time': access_time,
                    'action': 'open'
                }).execute()

                message = f"Locker {locker_number} is now occupied by you"

            elif locker['status'] == 'occupied' and locker['user_id'] == user_id:
                # Release the locker
                supabase.table('lockers').update({
                    'status': 'available',
                    'user_id': None
                }).eq('id', locker_id).execute()

                # Log the access
                supabase.table('access_logs').insert({
                    'user_id': user_id,
                    'locker_id': locker_id,
                    'access_time': access_time,
                    'action': 'close'
                }).execute()

                message = f"Locker {locker_number} is now available"

            return jsonify({"status": "success", "message": message})

        else:
            # No lockers available for the user
            available_locker_response = supabase.table('lockers').select('*').eq('status', 'available').limit(1).execute()
            if available_locker_response.data:
                available_locker = available_locker_response.data[0]
                locker_id = available_locker['id']
                locker_number = available_locker['locker_number']

                # Assign the locker to the user
                supabase.table('lockers').update({
                    'status': 'occupied',
                    'user_id': user_id
                }).eq('id', locker_id).execute()

                # Log the access
                supabase.table('access_logs').insert({
                    'user_id': user_id,
                    'locker_id': locker_id,
                    'access_time': access_time,
                    'action': 'open'
                }).execute()

                return jsonify({"status": "success", "message": f"Locker {locker_number} is now assigned to you"})
            else:
                return jsonify({"status": "error", "message": "No available lockers"}), 403

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


        
@app.route('/view_users')
def view_users():
    response = supabase.table('users').select('*').execute()
    users = response.data
    return render_template('view_users.html', users=users)

@app.route('/view_lockers')
def view_lockers():
    response = supabase.table('lockers').select('*').execute()
    lockers = response.data
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

    # Base query for filters
    base_query = supabase.table('access_logs').select('id')  # Only fetch IDs for counting

    # Apply filters to the base query
    if user_filter:
        base_query = base_query.filter('users.username', 'eq', user_filter)
    
    if status_filter:
        base_query = base_query.filter('action', 'eq', status_filter.lower())

    if start_date:
        base_query = base_query.filter('access_time', 'gte', f"{start_date}T00:00:00")

    if end_date:
        base_query = base_query.filter('access_time', 'lte', f"{end_date}T23:59:59")

    if locker_number_filter:
        base_query = base_query.filter('lockers.locker_number', 'eq', locker_number_filter)

    # Fetch total record count
    total_records_response = base_query.execute()
    total_records = len(total_records_response.data)

    # Calculate total pages
    total_pages = (total_records + per_page - 1) // per_page

    # Fetch paginated data with sorting
    query = supabase.table('access_logs') \
        .select('locker_id, user_id, access_time, action, lockers(locker_number), users(username, rfid_tag)') \
        .order('access_time', desc=True) \
        .range((page - 1) * per_page, page * per_page - 1)

    # Apply the same filters to the query
    if user_filter:
        query = query.filter('users.username', 'eq', user_filter)

    if status_filter:
        query = query.filter('action', 'eq', status_filter.lower())

    if start_date:
        query = query.filter('access_time', 'gte', f"{start_date}T00:00:00")

    if end_date:
        query = query.filter('access_time', 'lte', f"{end_date}T23:59:59")

    if locker_number_filter:
        query = query.filter('lockers.locker_number', 'eq', locker_number_filter)

    # Execute the query and fetch data
    access_logs_response = query.execute()
    access_logs = access_logs_response.data

    # Merge the access logs with user and locker details
    monitoring_data = []
    for log in access_logs:
        locker_number = log['lockers']['locker_number'] if log.get('lockers') else 'No Locker Data'
        username = log['users']['username'] if log.get('users') else 'No User Data'
        rfid_tag = log['users']['rfid_tag'] if log.get('users') else 'No RFID Data'

        monitoring_data.append({
            'locker_number': locker_number,
            'username': username,
            'rfid_tag': rfid_tag,
            'access_time': log['access_time'],
            'action': log['action']
        })

    return render_template(
        'monitoring.html', 
        monitoring_data=monitoring_data, 
        page=page, 
        total_pages=total_pages
    )




# Endpoint untuk menambahkan loker
@app.route('/add_locker', methods=['GET', 'POST'])
def add_locker():
    if request.method == 'POST':
        locker_number = request.form['locker_number']

        try:
            response = supabase.table('lockers').insert({
                'locker_number': locker_number,
                'status': 'available'
            }).execute()
            if response.error:
                flash('Locker number already exists!', 'error')
            else:
                flash('Locker added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding locker: {e}', 'error')

        return render_template('add_locker.html')

    return render_template('add_locker.html')

# CRUD for Users
@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    if request.method == 'POST':
        username = request.form['username']
        pin = request.form['pin']
        rfid_tag = request.form['rfid_tag']
        try:
            response = supabase.table('users').insert({
                'username': username,
                'pin': pin,
                'rfid_tag': rfid_tag
            }).execute()
            if response.error:
                flash('Username or RFID tag already exists!', 'error')
            else:
                flash('User added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding user: {e}', 'error')

    response = supabase.table('users').select('*').execute()
    users = response.data if response.data else []
    return render_template('view_users.html', users=users)

@app.route('/users/update/<int:user_id>', methods=['GET', 'POST'])
def update_user(user_id):
    if request.method == 'POST':
        username = request.form['username']
        pin = request.form['pin']
        rfid_tag = request.form['rfid_tag']
        try:
            supabase.table('users').update({
                'username': username,
                'pin': pin,
                'rfid_tag': rfid_tag
            }).eq('id', user_id).execute()
            flash('User updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating user: {e}', 'error')
        return redirect(url_for('manage_users'))

    response = supabase.table('users').select('*').eq('id', user_id).execute()
    user = response.data[0] if response.data else None
    if not user:
        flash('User not found!', 'error')
        return redirect(url_for('manage_users'))

    return render_template('update_user.html', user=user)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        supabase.table('users').delete().eq('id', user_id).execute()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting user: {e}', 'error')
    return redirect(url_for('manage_users'))

# CRUD for Lockers
@app.route('/lockers', methods=['GET', 'POST'])
def manage_lockers():
    if request.method == 'POST':
        locker_number = request.form['locker_number']
        try:
            # Insert new locker into the database
            response = supabase.table('lockers').insert({
                'locker_number': locker_number,
                'status': 'available'
            }).execute()
            if response.error:
                flash('Locker number already exists!', 'error')
            else:
                flash('Locker added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding locker: {e}', 'error')

    # Fetch all lockers from the database
    try:
        response = supabase.table('lockers').select('*').execute()
        lockers = response.data if response.data else []
    except Exception as e:
        lockers = []
        flash(f'Error retrieving lockers: {e}', 'error')

    return render_template('view_lockers.html', lockers=lockers)


@app.route('/lockers/update/<int:locker_id>', methods=['GET', 'POST'])
def update_locker(locker_id):
    if request.method == 'POST':
        locker_number = request.form['locker_number']
        try:
            # Update locker details in the database
            response = supabase.table('lockers').update({
                'locker_number': locker_number
            }).eq('id', locker_id).execute()
            if response.error:
                flash('Error updating locker!', 'error')
            else:
                flash('Locker updated successfully!', 'success')
            return redirect(url_for('manage_lockers'))
        except Exception as e:
            flash(f'Error updating locker: {e}', 'error')

    # Fetch locker details for the given ID
    try:
        response = supabase.table('lockers').select('*').eq('id', locker_id).execute()
        locker = response.data[0] if response.data else None
    except Exception as e:
        locker = None
        flash(f'Error retrieving locker: {e}', 'error')

    if not locker:
        flash('Locker not found!', 'error')
        return redirect(url_for('manage_lockers'))

    return render_template('update_locker.html', locker=locker)


@app.route('/lockers/delete/<int:locker_id>', methods=['POST'])
def delete_locker(locker_id):
    try:
        # Delete locker from the database
        response = supabase.table('lockers').delete().eq('id', locker_id).execute()
        if response.error:
            flash('Error deleting locker!', 'error')
        else:
            flash('Locker deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting locker: {e}', 'error')

    return redirect(url_for('manage_lockers'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
