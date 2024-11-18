@app.route('/rfid', methods=['POST'])
def rfid_access():
    rfid_tag = request.form.get('rfid')
    if not rfid_tag:
        return jsonify({"status": "error", "message": "No RFID provided"}), 400

    response = supabase.table('users').select("*").eq('rfid_tag', rfid_tag).execute()
    if not response.data:
        return jsonify({"status": "error", "message": "RFID not recognized"}), 403

    user = response.data[0]
    user_id = user['id']

    response = supabase.table('lockers').select("*").or_("status.eq.available,status.eq.occupied&user_id.eq." + str(user_id)).execute()
    locker = response.data[0] if response.data else None

    if locker:
        locker_id = locker['id']
        locker_number = locker['locker_number']

        access_time = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')

        if locker['status'] == 'available':
            supabase.table('lockers').update({'status': 'occupied', 'user_id': user_id}).eq('id', locker_id).execute()
            supabase.table('access_logs').insert({"user_id": user_id, "locker_id": locker_id, "access_time": access_time, "action": 'open'}).execute()
            message = f"Locker {locker_number} is now occupied by you"

        elif locker['status'] == 'occupied' and locker['user_id'] == user_id:
            supabase.table('lockers').update({'status': 'available', 'user_id': None}).eq('id', locker_id).execute()
            supabase.table('access_logs').insert({"user_id": user_id, "locker_id": locker_id, "access_time": access_time, "action": 'close'}).execute()
            message = f"Locker {locker_number} is now available"

        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": "Locker is currently occupied by another user"}), 403