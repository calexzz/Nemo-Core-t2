import sqlite3
import hashlib

DB_PATH = 'schedule.db'

def get_db():
    """Подключение к БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Хэш пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Создание таблиц и тестовых данных"""
    conn = get_db()
    c = conn.cursor()

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

    # Уведомления для админов.
    # Используется когда сотрудник отменяет рабочий день.
    # (уведомление админам на случай если чел умирает от температуры в 37C и отменяет рабочий день)
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            shift_id INTEGER,
            shift_date TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Запросы на переработку (превышение 40 ч/неделю)
    c.execute('''
        CREATE TABLE IF NOT EXISTS overtime_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            shift_id INTEGER NOT NULL,
            week_start TEXT NOT NULL,
            planned_hours REAL NOT NULL,
            extra_hours REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            admin_comment TEXT,
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (shift_id) REFERENCES shifts(id)
        )
    ''')

    conn.commit()

    users = [
        ('admin',    'admin123',  'Администратор',                 'admin',    None,         None),
        ('manager1', 'pass1234',  'Пупкин Иван Иванович',          'manager',  'Пупкина',    None),
        ('manager2', 'pass1234',  'Тумбочкин Петр Петрович',       'manager',  'Тумбочкина', None),
        ('siz_alex', 'pass1234',  'Сизый Александр Петрович',      'employee', 'Пупкина',    'Группа Сизых'),
        ('siz_mar',  'pass1234',  'Сизый Мария Ивановна',          'employee', 'Пупкина',    'Группа Сизых'),
        ('vas_ivan', 'pass1234',  'Васильков Иван Сергеевич',      'employee', 'Пупкина',    'Группа Василькова'),
        ('vas_olga', 'pass1234',  'Василькова Ольга Васильевна',   'employee', 'Пупкина',    'Группа Василькова'),
        ('kuz_vikt', 'pass1234',  'Кузнецов Виктор Михайлович',    'employee', 'Тумбочкина', 'Группа Кузнецовых'),
        ('kuz_svet', 'pass1234',  'Кузнецова Светлана Викторовна', 'employee', 'Тумбочкина', 'Группа Кузнецовых'),
    ]

    for username, password, full_name, role, alliance, team in users:
        try:
            c.execute(
                'INSERT INTO users (username, password, full_name, role, alliance, team) VALUES (?,?,?,?,?,?)',
                (username, hash_password(password), full_name, role, alliance, team)
            )
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
