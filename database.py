import sqlite3
import hashlib
import csv
import os

DB_PATH = 'schedule.db'
CSV_PATH = 'users.csv'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users_from_csv():
    """Загружает пользователей из CSV-файла, если он существует и таблица users пуста"""
    if not os.path.exists(CSV_PATH):
        return False
    conn = get_db()
    c = conn.cursor()
    # Проверяем, есть ли уже пользователи
    c.execute("SELECT COUNT(*) as cnt FROM users")
    count = c.fetchone()['cnt']
    if count > 0:
        conn.close()
        return False
    # Загружаем из CSV
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                c.execute(
                    'INSERT INTO users (username, password, full_name, role, alliance, team) VALUES (?,?,?,?,?,?)',
                    (row['username'], hash_password(row['password']), row['full_name'], row['role'], row['alliance'] or None, row['team'] or None)
                )
            except sqlite3.IntegrityError:
                pass  # игнорируем дубликаты
    conn.commit()
    conn.close()
    return True

def init_db():
    """Создание таблиц и загрузка данных из CSV"""
    conn = get_db()
    c = conn.cursor()

    # Таблица пользователей
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            alliance TEXT,
            team TEXT
        )
    ''')

    # Таблица смен
    c.execute('''
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            shift_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT DEFAULT 'plan',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Таблица заявок
    c.execute('''
        CREATE TABLE IF NOT EXISTS shift_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            shift_id INTEGER,
            shift_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            request_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (shift_id) REFERENCES shifts(id)
        )
    ''')

    conn.commit()
    conn.close()

    # Загружаем пользователей из CSV, если таблица пуста
    load_users_from_csv()