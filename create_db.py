import sqlite3

def create_database():
    conn = sqlite3.connect('smart_locker.db')
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        pin TEXT NOT NULL,  -- Kolom PIN
        rfid_tag TEXT NOT NULL UNIQUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lockers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        locker_number TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'available',  -- status bisa 'available' atau 'occupied'
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS access_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        locker_id INTEGER,
        access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        action TEXT NOT NULL,  -- action bisa 'open' atau 'close'
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (locker_id) REFERENCES lockers(id)
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lockers_status ON lockers(status);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_rfid_tag ON users(rfid_tag);')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_database()
