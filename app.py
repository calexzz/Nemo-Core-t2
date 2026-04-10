from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import sqlite3
import io
import openpyxl
from datetime import datetime, timedelta
from database import get_db, hash_password, init_db

app = Flask(__name__)
app.secret_key = 'hackathon_t2_secret_key_2024'

# ─── Вспомогательные функции ───────────────────────────────────────────────────

def login_required(f):
    """Декоратор: проверка авторизации"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    """Декоратор: проверка роли"""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_next_14_days():
    """Список дат на следующие 14 дней"""
    today = datetime.today()
    days = []
    weekdays_ru = ['Понедельник','Вторник','Среда','Четверг','Пятница','Суббота','Воскресенье']
    for i in range(14):
        d = today + timedelta(days=i)
        days.append({
            'value': d.strftime('%Y-%m-%d'),
            'label': f"{d.strftime('%Y-%m-%d')} ({weekdays_ru[d.weekday()]})"
        })
    return days

def check_consecutive_shifts(user_id, new_date, exclude_id=None):
    """Проверка: нет ли 6 смен подряд при добавлении новой даты"""
    conn = get_db()
    q = 'SELECT shift_date FROM shifts WHERE user_id=? AND start_time != "Выходной"'
    params = [user_id]
    if exclude_id:
        q += ' AND id != ?'
        params.append(exclude_id)
    rows = conn.execute(q, params).fetchall()
    conn.close()

    dates = sorted(set([r['shift_date'] for r in rows] + [new_date]))
    max_consecutive = 0
    current = 1
    for i in range(1, len(dates)):
        d1 = datetime.strptime(dates[i-1], '%Y-%m-%d')
        d2 = datetime.strptime(dates[i], '%Y-%m-%d')
        if (d2 - d1).days == 1:
            current += 1
        else:
            current = 1
        max_consecutive = max(max_consecutive, current)
    return max(max_consecutive, 1 if dates else 0)

# ─── Маршруты ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    role = session.get('role')
    if role in ('admin', 'manager'):
        return redirect(url_for('manager_dashboard'))
    return redirect(url_for('employee_schedule'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username=? AND password=?',
            (username, hash_password(password))
        ).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            session['alliance'] = user['alliance']
            session['team'] = user['team']
            return redirect(url_for('index'))
        else:
            error = 'Неверный логин или пароль'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── Страница сотрудника ───────────────────────────────────────────────────────

@app.route('/schedule')
@login_required
def employee_schedule():
    user_id = session['user_id']
    conn = get_db()
    shifts = conn.execute(
        'SELECT * FROM shifts WHERE user_id=? ORDER BY shift_date',
        (user_id,)
    ).fetchall()
    conn.close()
    dates = get_next_14_days()
    return render_template('employee.html',
        shifts=shifts,
        dates=dates,
        user=session
    )

@app.route('/shift/add', methods=['POST'])
@login_required
def add_shift():
    user_id = session['user_id']
    shift_date = request.form['shift_date']
    start_time = request.form['start_time']
    end_time = request.form.get('end_time', '')

    # Проверяем: нет ли уже смены на эту дату
    conn = get_db()
    existing = conn.execute(
        'SELECT id FROM shifts WHERE user_id=? AND shift_date=?',
        (user_id, shift_date)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'На эту дату уже добавлена смена'}), 400

    # Проверяем лимит 6 смен подряд
    if start_time != 'Выходной':
        consecutive = check_consecutive_shifts(user_id, shift_date)
        if consecutive > 6:
            conn.close()
            return jsonify({'error': f'Будет {consecutive} смен подряд! Максимум — 6.'}), 400

    conn.execute(
        'INSERT INTO shifts (user_id, shift_date, start_time, end_time) VALUES (?,?,?,?)',
        (user_id, shift_date, start_time, end_time)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/shift/delete/<int:shift_id>', methods=['POST'])
@login_required
def delete_shift(shift_id):
    user_id = session['user_id']
    conn = get_db()
    # Сотрудник может удалять только свои смены; менеджер/админ — любые
    if session['role'] == 'employee':
        conn.execute('DELETE FROM shifts WHERE id=? AND user_id=?', (shift_id, user_id))
    else:
        conn.execute('DELETE FROM shifts WHERE id=?', (shift_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/shift/edit/<int:shift_id>', methods=['POST'])
@login_required
def edit_shift(shift_id):
    user_id = session['user_id']
    start_time = request.form['start_time']
    end_time = request.form.get('end_time', '')
    conn = get_db()
    shift = conn.execute('SELECT * FROM shifts WHERE id=?', (shift_id,)).fetchone()
    if not shift:
        conn.close()
        return jsonify({'error': 'Смена не найдена'}), 404
    # Проверка доступа
    if session['role'] == 'employee' and shift['user_id'] != user_id:
        conn.close()
        return jsonify({'error': 'Нет доступа'}), 403

    if start_time != 'Выходной':
        consecutive = check_consecutive_shifts(user_id, shift['shift_date'], exclude_id=shift_id)
        if consecutive > 6:
            conn.close()
            return jsonify({'error': f'Будет {consecutive} смен подряд! Максимум — 6.'}), 400

    conn.execute(
        'UPDATE shifts SET start_time=?, end_time=? WHERE id=?',
        (start_time, end_time, shift_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ─── Страница руководителя ─────────────────────────────────────────────────────

@app.route('/manager')
@login_required
@role_required('admin', 'manager')
def manager_dashboard():
    conn = get_db()

    # Менеджер видит только свой альянс; админ — всех
    if session['role'] == 'admin':
        employees = conn.execute(
            "SELECT * FROM users WHERE role='employee' ORDER BY alliance, team, full_name"
        ).fetchall()
    else:
        employees = conn.execute(
            "SELECT * FROM users WHERE role='employee' AND alliance=? ORDER BY team, full_name",
            (session['alliance'],)
        ).fetchall()

    # Собираем смены для всех сотрудников
    employee_ids = [e['id'] for e in employees]
    shifts_by_user = {}
    if employee_ids:
        placeholders = ','.join('?' * len(employee_ids))
        shifts = conn.execute(
            f'SELECT * FROM shifts WHERE user_id IN ({placeholders}) ORDER BY shift_date',
            employee_ids
        ).fetchall()
        for s in shifts:
            shifts_by_user.setdefault(s['user_id'], []).append(dict(s))

    conn.close()

    employees_data = []
    for emp in employees:
        emp_shifts = shifts_by_user.get(emp['id'], [])
        total = len([s for s in emp_shifts if s['start_time'] != 'Выходной'])
        employees_data.append({
            **dict(emp),
            'shifts': emp_shifts,
            'total_shifts': total
        })

    return render_template('manager.html',
        employees=employees_data,
        user=session,
        dates=get_next_14_days()
    )

# ─── API для менеджера ─────────────────────────────────────────────────────────

@app.route('/api/employee/<int:emp_id>/shifts')
@login_required
@role_required('admin', 'manager')
def get_employee_shifts(emp_id):
    conn = get_db()
    shifts = conn.execute(
        'SELECT * FROM shifts WHERE user_id=? ORDER BY shift_date',
        (emp_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(s) for s in shifts])

@app.route('/api/users', methods=['GET'])
@login_required
@role_required('admin', 'manager')
def get_users():
    conn = get_db()
    if session['role'] == 'admin':
        users = conn.execute("SELECT id,username,full_name,role,alliance,team FROM users ORDER BY role,alliance,full_name").fetchall()
    else:
        users = conn.execute("SELECT id,username,full_name,role,alliance,team FROM users WHERE alliance=? ORDER BY role,full_name", (session['alliance'],)).fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route('/api/users/add', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def add_user():
    data = request.json
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO users (username,password,full_name,role,alliance,team) VALUES (?,?,?,?,?,?)',
            (data['username'], hash_password(data['password']),
             data['full_name'], data['role'],
             data.get('alliance'), data.get('team'))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Логин уже занят'}), 400
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/users/delete/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    conn = get_db()
    conn.execute('DELETE FROM shifts WHERE user_id=?', (user_id,))
    conn.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ─── Выгрузка в Excel ─────────────────────────────────────────────────────────

@app.route('/export/excel')
@login_required
@role_required('admin', 'manager')
def export_excel():
    conn = get_db()

    if session['role'] == 'admin':
        employees = conn.execute(
            "SELECT * FROM users WHERE role='employee' ORDER BY alliance, team, full_name"
        ).fetchall()
    else:
        employees = conn.execute(
            "SELECT * FROM users WHERE role='employee' AND alliance=? ORDER BY team, full_name",
            (session['alliance'],)
        ).fetchall()

    # Диапазон дат: сегодня + 14 дней
    today = datetime.today()
    date_range = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(14)]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'График смен'

    # Заголовки
    headers = ['Альянс', 'Группа', 'Сотрудник'] + date_range
    ws.append(headers)

    # Стиль заголовка
    from openpyxl.styles import PatternFill, Font, Alignment
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = Font(color='FFFFFF', bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Данные
    employee_ids = [e['id'] for e in employees]
    shifts_map = {}
    if employee_ids:
        placeholders = ','.join('?' * len(employee_ids))
        shifts = conn.execute(
            f'SELECT * FROM shifts WHERE user_id IN ({placeholders})',
            employee_ids
        ).fetchall()
        for s in shifts:
            shifts_map[(s['user_id'], s['shift_date'])] = s

    conn.close()

    for emp in employees:
        row = [emp['alliance'] or '', emp['team'] or '', emp['full_name']]
        for date_str in date_range:
            shift = shifts_map.get((emp['id'], date_str))
            if shift:
                if shift['start_time'] == 'Выходной':
                    row.append('Выходной')
                else:
                    end = shift['end_time'] or ''
                    row.append(f"{shift['start_time']}-{end}" if end else shift['start_time'])
            else:
                row.append('')
        ws.append(row)

    # Авто-ширина колонок
    for col in ws.columns:
        max_len = max((len(str(cell.value or '')) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = max(max_len + 2, 10)

    # Отдаём файл
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"schedule_{today.strftime('%Y%m%d')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)

# ─── Запуск ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
