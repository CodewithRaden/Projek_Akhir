CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  pin TEXT NOT NULL,
  rfid_tag TEXT UNIQUE NOT NULL
);

CREATE TABLE lockers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  locker_number TEXT UNIQUE NOT NULL,
  status TEXT DEFAULT 'available',
  user_id INTEGER,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE access_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  locker_id INTEGER,
  access_time TEXT NOT NULL,
  action TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id),
  FOREIGN KEY(locker_id) REFERENCES lockers(id)
);
