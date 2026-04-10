import sqlite3
import hashlib
import os

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

    # Таблица заявок на изменение смен
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

    # Тестовые пользователи
    users = [
        ('admin', 'admin123', 'Администратор', 'admin', None, None),
        ('manager1', 'pass123', 'Пупкин Иван Иванович', 'manager', 'Пупкина', None),
        ('manager2', 'pass123', 'Тумбочкин Петр Петрович', 'manager', 'Тумбочкина', None),
        ('siz_alex', 'pass123', 'Сизый Александр Петрович', 'employee', 'Пупкина', 'Группа Сизых'),
        ('siz_mar', 'pass123', 'Сизый Мария Ивановна', 'employee', 'Пупкина', 'Группа Сизых'),
        ('vas_ivan', 'pass123', 'Васильков Иван Сергеевич', 'employee', 'Пупкина', 'Группа Василькова'),
        ('vas_olga', 'pass123', 'Василькова Ольга Васильевна', 'employee', 'Пупкина', 'Группа Василькова'),
        ('kuz_vikt', 'pass123', 'Кузнецов Виктор Михайлович', 'employee', 'Тумбочкина', 'Группа Кузнецовых'),
        ('kuz_svet', 'pass123', 'Кузнецова Светлана Викторовна', 'employee', 'Тумбочкина', 'Группа Кузнецовых'),
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