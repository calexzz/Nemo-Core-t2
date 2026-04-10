from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import sqlite3
import io
import openpyxl
from datetime import datetime, timedelta
from database import get_db, hash_password, init_db

app = Flask(__name__)
app.secret_key = 'hackathon_t2_secret_key_2024'

# ─── Вспомогательные функции ───────────────────────────────────────────────

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                return jsonify({'error': 'Доступ запрещён'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_next_14_days():
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

def validate_shift_time(start_time, end_time):
    allowed_hours = list(range(8, 21))
    try:
        if start_time == 'Выходной':
            return True
        sh = int(start_time.split(':')[0])
        eh = int(end_time.split(':')[0])
        if sh not in allowed_hours or eh not in allowed_hours:
            return False
        if eh <= sh:
            return False
        if start_time.split(':')[1] != '00' or end_time.split(':')[1] != '00':
            return False
        return True
    except:
        return False

def is_within_24h(shift_date, start_time):
    try:
        shift_datetime = datetime.strptime(f"{shift_date} {start_time}", "%Y-%m-%d %H:%M")
        now = datetime.now()
        diff = (shift_datetime - now).total_seconds() / 3600
        return diff >= 24
    except:
        return False

# ─── Маршруты авторизации ──────────────────────────────────────────────────

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

# ─── Сотрудник (только просмотр) ───────────────────────────────────────────

@app.route('/schedule')
@login_required
def employee_schedule():
    user_id = session['user_id']
    conn = get_db()
    shifts = [dict(row) for row in conn.execute(
        'SELECT * FROM shifts WHERE user_id=? ORDER BY shift_date',
        (user_id,)
    ).fetchall()]
    conn.close()
    dates = get_next_14_days()
    return render_template('employee.html',
        shifts=shifts,
        dates=dates,
        user=session
    )

# ─── Заявки сотрудников ────────────────────────────────────────────────────

@app.route('/api/request/add', methods=['POST'])
@login_required
def request_add_shift():
    if session['role'] != 'employee':
        return jsonify({'error': 'Только сотрудники могут подавать заявки'}), 403

    data = request.json
    shift_date = data.get('shift_date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')

    if not shift_date or not start_time:
        return jsonify({'error': 'Укажите дату и время начала'}), 400

    if start_time != 'Выходной':
        if not validate_shift_time(start_time, end_time):
            return jsonify({'error': 'Время должно быть целым часом от 08:00 до 20:00, конец после начала'}), 400
        if not is_within_24h(shift_date, start_time):
            return jsonify({'error': 'Смену можно запросить минимум за 24 часа до начала'}), 400
    else:
        end_time = ''
        if not is_within_24h(shift_date, '00:00'):
            return jsonify({'error': 'Выходной можно запросить минимум за 24 часа'}), 400

    conn = get_db()
    existing = conn.execute(
        'SELECT id FROM shifts WHERE user_id=? AND shift_date=?',
        (session['user_id'], shift_date)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'На эту дату уже есть смена. Подайте заявку на удаление.'}), 400

    conn.execute(
        'INSERT INTO shift_requests (user_id, shift_date, start_time, end_time, request_type) VALUES (?,?,?,?,?)',
        (session['user_id'], shift_date, start_time, end_time, 'add')
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': 'Заявка отправлена'})

@app.route('/api/request/delete', methods=['POST'])
@login_required
def request_delete_shift():
    if session['role'] != 'employee':
        return jsonify({'error': 'Только сотрудники могут подавать заявки'}), 403

    shift_id = request.json.get('shift_id')
    if not shift_id:
        return jsonify({'error': 'Не указана смена'}), 400

    conn = get_db()
    shift = conn.execute('SELECT * FROM shifts WHERE id=? AND user_id=?', (shift_id, session['user_id'])).fetchone()
    if not shift:
        conn.close()
        return jsonify({'error': 'Смена не найдена'}), 404

    if shift['start_time'] != 'Выходной':
        if not is_within_24h(shift['shift_date'], shift['start_time']):
            conn.close()
            return jsonify({'error': 'Удаление можно запросить минимум за 24 часа до начала'}), 400
    else:
        if not is_within_24h(shift['shift_date'], '00:00'):
            conn.close()
            return jsonify({'error': 'Удаление выходного можно запросить минимум за 24 часа'}), 400

    existing_req = conn.execute(
        'SELECT id FROM shift_requests WHERE shift_id=? AND status="pending"',
        (shift_id,)
    ).fetchone()
    if existing_req:
        conn.close()
        return jsonify({'error': 'Заявка на удаление уже отправлена'}), 400

    conn.execute(
        'INSERT INTO shift_requests (user_id, shift_id, shift_date, start_time, end_time, request_type) VALUES (?,?,?,?,?,?)',
        (session['user_id'], shift_id, shift['shift_date'], shift['start_time'], shift['end_time'], 'delete')
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': 'Заявка на удаление отправлена'})

@app.route('/api/my_requests')
@login_required
def my_requests():
    conn = get_db()
    reqs = conn.execute(
        'SELECT * FROM shift_requests WHERE user_id=? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in reqs])

# ─── Менеджер: управление сменами (прямое) ─────────────────────────────────

@app.route('/manager')
@login_required
@role_required('admin', 'manager')
def manager_dashboard():
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

@app.route('/api/shift/assign', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def assign_shift():
    data = request.json
    employee_id = data.get('employee_id')
    shift_date = data.get('shift_date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')

    if not all([employee_id, shift_date, start_time]):
        return jsonify({'error': 'Не все поля заполнены'}), 400

    today = datetime.today().date()
    try:
        date_obj = datetime.strptime(shift_date, '%Y-%m-%d').date()
        if not (today <= date_obj <= today + timedelta(days=13)):
            return jsonify({'error': 'Дата должна быть в пределах следующих 14 дней'}), 400
    except:
        return jsonify({'error': 'Неверный формат даты'}), 400

    if start_time != 'Выходной':
        if not validate_shift_time(start_time, end_time):
            return jsonify({'error': 'Время должно быть целым часом от 08:00 до 20:00, конец после начала'}), 400
    else:
        end_time = ''

    conn = get_db()
    emp = conn.execute('SELECT alliance FROM users WHERE id=?', (employee_id,)).fetchone()
    if not emp:
        conn.close()
        return jsonify({'error': 'Сотрудник не найден'}), 404
    if session['role'] == 'manager' and emp['alliance'] != session['alliance']:
        conn.close()
        return jsonify({'error': 'Вы можете назначать смены только сотрудникам вашего альянса'}), 403

    existing = conn.execute(
        'SELECT id FROM shifts WHERE user_id=? AND shift_date=?',
        (employee_id, shift_date)
    ).fetchone()
    if existing:
        shift_id = existing['id']
        if start_time != 'Выходной':
            consecutive = check_consecutive_shifts(employee_id, shift_date, exclude_id=shift_id)
            if consecutive > 6:
                conn.close()
                return jsonify({'error': f'Будет {consecutive} смен подряд! Максимум — 6.'}), 400
        conn.execute(
            'UPDATE shifts SET start_time=?, end_time=? WHERE id=?',
            (start_time, end_time, shift_id)
        )
    else:
        if start_time != 'Выходной':
            consecutive = check_consecutive_shifts(employee_id, shift_date)
            if consecutive > 6:
                conn.close()
                return jsonify({'error': f'Будет {consecutive} смен подряд! Максимум — 6.'}), 400
        conn.execute(
            'INSERT INTO shifts (user_id, shift_date, start_time, end_time) VALUES (?,?,?,?)',
            (employee_id, shift_date, start_time, end_time)
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/shift/delete/<int:shift_id>', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def delete_shift_api(shift_id):
    conn = get_db()
    shift = conn.execute('SELECT user_id FROM shifts WHERE id=?', (shift_id,)).fetchone()
    if not shift:
        conn.close()
        return jsonify({'error': 'Смена не найдена'}), 404
    if session['role'] == 'manager':
        emp = conn.execute('SELECT alliance FROM users WHERE id=?', (shift['user_id'],)).fetchone()
        if emp['alliance'] != session['alliance']:
            conn.close()
            return jsonify({'error': 'Нет доступа'}), 403
    conn.execute('DELETE FROM shifts WHERE id=?', (shift_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ─── Менеджер: заявки ──────────────────────────────────────────────────────

@app.route('/api/requests')
@login_required
@role_required('admin', 'manager')
def get_requests():
    conn = get_db()
    if session['role'] == 'admin':
        requests = conn.execute('''
            SELECT r.*, u.full_name, u.alliance, u.team
            FROM shift_requests r
            JOIN users u ON r.user_id = u.id
            WHERE r.status = 'pending'
            ORDER BY r.created_at DESC
        ''').fetchall()
    else:
        requests = conn.execute('''
            SELECT r.*, u.full_name, u.alliance, u.team
            FROM shift_requests r
            JOIN users u ON r.user_id = u.id
            WHERE r.status = 'pending' AND u.alliance = ?
            ORDER BY r.created_at DESC
        ''', (session['alliance'],)).fetchall()
    conn.close()
    return jsonify([dict(req) for req in requests])

@app.route('/api/request/approve/<int:req_id>', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def approve_request(req_id):
    conn = get_db()
    req = conn.execute('SELECT * FROM shift_requests WHERE id=? AND status="pending"', (req_id,)).fetchone()
    if not req:
        conn.close()
        return jsonify({'error': 'Заявка не найдена или уже обработана'}), 404

    if session['role'] == 'manager':
        emp = conn.execute('SELECT alliance FROM users WHERE id=?', (req['user_id'],)).fetchone()
        if emp['alliance'] != session['alliance']:
            conn.close()
            return jsonify({'error': 'Нет доступа'}), 403

    try:
        if req['request_type'] == 'add':
            if req['start_time'] != 'Выходной':
                consecutive = check_consecutive_shifts(req['user_id'], req['shift_date'])
                if consecutive > 6:
                    conn.close()
                    return jsonify({'error': f'Будет {consecutive} смен подряд! Максимум — 6.'}), 400
            existing = conn.execute(
                'SELECT id FROM shifts WHERE user_id=? AND shift_date=?',
                (req['user_id'], req['shift_date'])
            ).fetchone()
            if existing:
                conn.close()
                return jsonify({'error': 'Смена на эту дату уже существует'}), 400
            conn.execute(
                'INSERT INTO shifts (user_id, shift_date, start_time, end_time) VALUES (?,?,?,?)',
                (req['user_id'], req['shift_date'], req['start_time'], req['end_time'])
            )
        else:  # delete
            conn.execute('DELETE FROM shifts WHERE id=?', (req['shift_id'],))

        conn.execute('UPDATE shift_requests SET status="approved" WHERE id=?', (req_id,))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/request/reject/<int:req_id>', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def reject_request(req_id):
    conn = get_db()
    req = conn.execute('SELECT * FROM shift_requests WHERE id=? AND status="pending"', (req_id,)).fetchone()
    if not req:
        conn.close()
        return jsonify({'error': 'Заявка не найдена'}), 404
    if session['role'] == 'manager':
        emp = conn.execute('SELECT alliance FROM users WHERE id=?', (req['user_id'],)).fetchone()
        if emp['alliance'] != session['alliance']:
            conn.close()
            return jsonify({'error': 'Нет доступа'}), 403
    conn.execute('UPDATE shift_requests SET status="rejected" WHERE id=?', (req_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ─── Управление пользователями (только admin) ──────────────────────────────

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
@role_required('admin')
def add_user():
    data = request.json
    password = data.get('password', '')
    if len(password) < 6 or len(password) > 24:
        return jsonify({'error': 'Пароль должен быть от 6 до 24 символов'}), 400

    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO users (username,password,full_name,role,alliance,team) VALUES (?,?,?,?,?,?)',
            (data['username'], hash_password(password),
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
    conn.execute('DELETE FROM shift_requests WHERE user_id=?', (user_id,))
    conn.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ─── Выгрузка в Excel ──────────────────────────────────────────────────────

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

    today = datetime.today()
    date_range = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(14)]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'График смен'

    headers = ['Альянс', 'Группа', 'Сотрудник'] + date_range
    ws.append(headers)

    from openpyxl.styles import PatternFill, Font, Alignment
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = Font(color='FFFFFF', bold=True)
        cell.alignment = Alignment(horizontal='center')

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

    for col in ws.columns:
        max_len = max((len(str(cell.value or '')) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = max(max_len + 2, 10)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"schedule_{today.strftime('%Y%m%d')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)