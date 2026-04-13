import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from datetime import datetime, timedelta

from config import Config
from database import (users_collection, students_collection, teachers_collection, 
                      attendance_collection, announcements_collection, fees_collection, 
                      settings_collection, salaries_collection, expenses_collection, 
                      infrastructure_collection, library_collection)

app = Flask(__name__)
app.config.from_object(Config)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- AUTH ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        elif role == 'student':
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        contact = request.form.get('contact', '')
        
        # Prevent registering multiple admins easily, but for demo allow
        # In actual prod, admin registration would be restricted
        
        if users_collection.find_one({'email': email}):
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        
        user_id = users_collection.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
            'role': role
        }).inserted_id
        
        if role == 'student':
            students_collection.insert_one({
                '_id': user_id,
                'name': username,
                'email': email,
                'roll': '',
                'department': '',
                'contact': contact,
                'picture': '',
                'created_at': datetime.now()
            })
        elif role == 'teacher':
            teachers_collection.insert_one({
                '_id': user_id,
                'name': username,
                'email': email,
                'contact': contact,
                'subject': ''
            })
            
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# --- ADMIN ROUTES ---
@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    total_students = students_collection.count_documents({})
    total_teachers = teachers_collection.count_documents({})
    total_users = users_collection.count_documents({})
    
    dates = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    present_counts = [45, 48, 42, 50, 47]
    today_present = 47
    today_absent = 5
    avg_attendance = 92
    
    return render_template('admin_dashboard.html', 
                          total_students=total_students,
                          total_teachers=total_teachers,
                          total_users=total_users,
                          avg_attendance=avg_attendance,
                          dates=dates,
                          present_counts=present_counts,
                          today_present=today_present,
                          today_absent=today_absent)

# --- ADMIN STUDENT MANAGEMENT ---
@app.route('/admin/students', methods=['GET'])
@login_required
@role_required('admin')
def admin_students():
    students = list(students_collection.find())
    return render_template('students.html', students=students)

@app.route('/admin/student/add', methods=['POST'])
@login_required
@role_required('admin')
def add_student():
    name = request.form.get('name')
    email = request.form.get('email')
    roll = request.form.get('roll')
    department = request.form.get('department')
    password = request.form.get('password')
    contact = request.form.get('contact', '')
    
    picture_filename = ''
    if 'picture' in request.files:
        pic = request.files['picture']
        if pic.filename != '':
            filename = secure_filename(pic.filename)
            pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            picture_filename = filename
    
    if users_collection.find_one({'email': email}):
        flash('Email already registered', 'danger')
        return redirect(url_for('admin_students'))
        
    hashed_password = generate_password_hash(password)
    user_id = users_collection.insert_one({
        'username': name,
        'email': email,
        'password': hashed_password,
        'role': 'student'
    }).inserted_id
    
    students_collection.insert_one({
        '_id': user_id,
        'name': name,
        'email': email,
        'roll': roll,
        'department': department,
        'contact': contact,
        'picture': picture_filename,
        'created_at': datetime.now()
    })
    
    flash('Student added successfully!', 'success')
    return redirect(url_for('admin_students'))

@app.route('/admin/student/delete/<student_id>')
@login_required
@role_required('admin')
def delete_student(student_id):
    users_collection.delete_one({'_id': ObjectId(student_id)})
    students_collection.delete_one({'_id': ObjectId(student_id)})
    flash('Student deleted successfully', 'success')
    return redirect(url_for('admin_students'))

# --- ADMIN TEACHER MANAGEMENT ---
@app.route('/admin/teachers', methods=['GET'])
@login_required
@role_required('admin')
def admin_teachers():
    teachers = list(teachers_collection.find())
    return render_template('teachers.html', teachers=teachers)

@app.route('/admin/teacher/add', methods=['POST'])
@login_required
@role_required('admin')
def add_teacher():
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    password = request.form.get('password')
    contact = request.form.get('contact', '')
    
    if users_collection.find_one({'email': email}):
        flash('Email already registered', 'danger')
        return redirect(url_for('admin_teachers'))
        
    hashed_password = generate_password_hash(password)
    user_id = users_collection.insert_one({
        'username': name,
        'email': email,
        'password': hashed_password,
        'role': 'teacher'
    }).inserted_id
    
    teachers_collection.insert_one({
        '_id': user_id,
        'name': name,
        'email': email,
        'contact': contact,
        'subject': subject
    })
    
    flash('Teacher added successfully!', 'success')
    return redirect(url_for('admin_teachers'))

@app.route('/admin/teacher/delete/<teacher_id>')
@login_required
@role_required('admin')
def delete_teacher(teacher_id):
    users_collection.delete_one({'_id': ObjectId(teacher_id)})
    teachers_collection.delete_one({'_id': ObjectId(teacher_id)})
    flash('Teacher deleted successfully', 'success')
    return redirect(url_for('admin_teachers'))

# --- TEACHER ROUTES ---
@app.route('/teacher/dashboard')
@login_required
@role_required('teacher')
def teacher_dashboard():
    teacher_id = session.get('user_id')
    teacher = teachers_collection.find_one({'_id': ObjectId(teacher_id)})
    
    total_students = students_collection.count_documents({})
    today = datetime.now().strftime('%Y-%m-%d')
    today_records = attendance_collection.count_documents({'teacher_id': teacher_id, 'date': today})
    
    return render_template('teacher_dashboard.html', 
                          teacher=teacher,
                          total_students=total_students,
                          today_records=today_records,
                          today=today)

@app.route('/teacher/attendance', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def teacher_attendance():
    if request.method == 'POST':
        date = request.form.get('date')
        student_ids = request.form.getlist('student_id')
        
        teacher_id = session.get('user_id')
        
        for s_id in student_ids:
            status = request.form.get(f'status_{s_id}')
            if status:
                attendance_collection.update_one(
                    {'student_id': s_id, 'date': date},
                    {'$set': {
                        'teacher_id': teacher_id,
                        'status': status
                    }},
                    upsert=True
                )
            
        flash('Attendance updated successfully!', 'success')
        return redirect(url_for('teacher_attendance'))
        
    students = list(students_collection.find())
    today = datetime.now().strftime('%Y-%m-%d')
    
    attendance_records = list(attendance_collection.find({'date': today}))
    att_dict = {rec['student_id']: rec['status'] for rec in attendance_records}
    
    for student in students:
        s_id_str = str(student['_id'])
        student['today_status'] = att_dict.get(s_id_str, '')

    return render_template('attendance.html', students=students, today=today, role='teacher')

# --- ADMIN ATTENDANCE VIEW ---
@app.route('/admin/attendance')
@login_required
@role_required('admin')
def admin_attendance():
    students = list(students_collection.find())
    today = datetime.now().strftime('%Y-%m-%d')
    
    attendance_records = list(attendance_collection.find({'date': today}))
    att_dict = {rec['student_id']: rec['status'] for rec in attendance_records}
    
    present_count = 0
    absent_count = 0
    
    for student in students:
        s_id_str = str(student['_id'])
        status = att_dict.get(s_id_str, 'Not Marked')
        student['today_status'] = status
        if status == 'Present':
            present_count += 1
        elif status == 'Absent':
            absent_count += 1
            
    return render_template('attendance.html', students=students, today=today, role='admin', 
                           present_count=present_count, absent_count=absent_count)

# --- ADMIN SETTINGS ---
@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_settings():
    if request.method == 'POST':
        bank_account = request.form.get('bank_account')
        settings_collection.update_one(
            {'key': 'bank_account'},
            {'$set': {'value': bank_account}},
            upsert=True
        )
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin_settings'))
        
    bank_setting = settings_collection.find_one({'key': 'bank_account'})
    bank_account = bank_setting['value'] if bank_setting else ''
    
    return render_template('admin_settings.html', bank_account=bank_account)

# --- ADMIN SALARIES ---
@app.route('/admin/salaries', methods=['GET'])
@login_required
@role_required('admin')
def admin_salaries():
    salaries = list(salaries_collection.find().sort('created_at', -1))
    teachers = list(teachers_collection.find())
    
    teacher_map = {str(t['_id']): t['name'] for t in teachers}
    for sal in salaries:
        sal['teacher_name'] = teacher_map.get(str(sal.get('teacher_id')), 'Unknown Teacher')
        
    return render_template('salaries.html', salaries=salaries, teachers=teachers)

@app.route('/admin/salary/add', methods=['POST'])
@login_required
@role_required('admin')
def add_salary():
    teacher_id = request.form.get('teacher_id')
    amount = request.form.get('amount')
    month = request.form.get('month')
    
    salaries_collection.insert_one({
        'teacher_id': teacher_id,
        'amount': float(amount),
        'month': month,
        'status': 'Pending',
        'created_at': datetime.now()
    })
    
    flash('Salary record added successfully!', 'success')
    return redirect(url_for('admin_salaries'))

@app.route('/admin/salary/update/<salary_id>')
@login_required
@role_required('admin')
def update_salary_status(salary_id):
    sal = salaries_collection.find_one({'_id': ObjectId(salary_id)})
    if sal:
        new_status = 'Paid' if sal.get('status') == 'Pending' else 'Pending'
        salaries_collection.update_one({'_id': ObjectId(salary_id)}, {'$set': {'status': new_status}})
        flash('Salary status updated.', 'success')
    return redirect(url_for('admin_salaries'))

# --- ADMIN FEE MANAGEMENT ---
@app.route('/admin/fees', methods=['GET'])
@login_required
@role_required('admin')
def admin_fees():
    fees = list(fees_collection.find().sort('created_at', -1))
    students = list(students_collection.find())
    
    student_map = {str(s['_id']): s['name'] for s in students}
    for fee in fees:
        fee['student_name'] = student_map.get(str(fee.get('student_id')), 'Unknown Student')
        
    return render_template('admin_fees.html', fees=fees, students=students)

@app.route('/admin/fee/add', methods=['POST'])
@login_required
@role_required('admin')
def add_fee():
    student_id = request.form.get('student_id')
    amount = request.form.get('amount')
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    
    fees_collection.insert_one({
        'student_id': student_id,
        'amount': float(amount),
        'description': description,
        'due_date': due_date,
        'status': 'Pending',
        'created_at': datetime.now()
    })
    
    flash('Fee assigned successfully!', 'success')
    return redirect(url_for('admin_fees'))

@app.route('/admin/fee/update/<fee_id>')
@login_required
@role_required('admin')
def update_fee_status(fee_id):
    fee = fees_collection.find_one({'_id': ObjectId(fee_id)})
    if fee:
        new_status = 'Paid' if fee.get('status') == 'Pending' else 'Pending'
        fees_collection.update_one({'_id': ObjectId(fee_id)}, {'$set': {'status': new_status}})
        flash('Fee status updated.', 'success')
    return redirect(url_for('admin_fees'))

# --- ADMIN EXPENSES MANAGEMENT ---
@app.route('/admin/expenses', methods=['GET'])
@login_required
@role_required('admin')
def admin_expenses():
    expenses = list(expenses_collection.find().sort('date', -1))
    total_expenses = sum(e['amount'] for e in expenses)
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('expenses.html', expenses=expenses, total_expenses=total_expenses, today=today)

@app.route('/admin/expense/add', methods=['POST'])
@login_required
@role_required('admin')
def add_expense():
    description = request.form.get('description')
    amount = float(request.form.get('amount', 0))
    date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    expenses_collection.insert_one({
        'description': description,
        'amount': amount,
        'date': date,
        'created_at': datetime.now()
    })
    
    flash('Expense added successfully!', 'success')
    return redirect(url_for('admin_expenses'))

@app.route('/admin/expense/delete/<expense_id>')
@login_required
@role_required('admin')
def delete_expense(expense_id):
    expenses_collection.delete_one({'_id': ObjectId(expense_id)})
    flash('Expense deleted.', 'success')
    return redirect(url_for('admin_expenses'))

# --- ADMIN INFRASTRUCTURE MANAGEMENT ---
@app.route('/admin/infrastructure', methods=['GET'])
@login_required
@role_required('admin')
def admin_infrastructure():
    items = list(infrastructure_collection.find().sort('name', 1))
    return render_template('infrastructure.html', items=items)

@app.route('/admin/infrastructure/add', methods=['POST'])
@login_required
@role_required('admin')
def add_infrastructure():
    name = request.form.get('name')
    item_type = request.form.get('type')
    status = request.form.get('status')
    value = request.form.get('value', 0)
    
    infrastructure_collection.insert_one({
        'name': name,
        'type': item_type,
        'status': status,
        'value': float(value),
        'created_at': datetime.now()
    })
    
    flash('Infrastructure item added successfully!', 'success')
    return redirect(url_for('admin_infrastructure'))

@app.route('/admin/infrastructure/delete/<item_id>')
@login_required
@role_required('admin')
def delete_infrastructure(item_id):
    infrastructure_collection.delete_one({'_id': ObjectId(item_id)})
    flash('Item deleted.', 'success')
    return redirect(url_for('admin_infrastructure'))

# --- ADMIN LIBRARY MANAGEMENT ---
@app.route('/admin/library', methods=['GET'])
@login_required
@role_required('admin')
def admin_library():
    books = list(library_collection.find().sort('title', 1))
    return render_template('library.html', books=books)

@app.route('/admin/library/add', methods=['POST'])
@login_required
@role_required('admin')
def add_book():
    title = request.form.get('title')
    author = request.form.get('author')
    
    library_collection.insert_one({
        'title': title,
        'author': author,
        'status': 'Available',
        'issued_to': '',
        'created_at': datetime.now()
    })
    
    flash('Book added successfully!', 'success')
    return redirect(url_for('admin_library'))

@app.route('/admin/library/issue/<book_id>', methods=['POST'])
@login_required
@role_required('admin')
def issue_book(book_id):
    issued_to = request.form.get('issued_to')
    library_collection.update_one({'_id': ObjectId(book_id)}, {'$set': {'status': 'Issued', 'issued_to': issued_to}})
    flash(f'Book issued to {issued_to}.', 'success')
    return redirect(url_for('admin_library'))

@app.route('/admin/library/return/<book_id>')
@login_required
@role_required('admin')
def return_book(book_id):
    library_collection.update_one({'_id': ObjectId(book_id)}, {'$set': {'status': 'Available', 'issued_to': ''}})
    flash('Book returned successfully.', 'success')
    return redirect(url_for('admin_library'))

@app.route('/admin/library/delete/<book_id>')
@login_required
@role_required('admin')
def delete_book(book_id):
    library_collection.delete_one({'_id': ObjectId(book_id)})
    flash('Book deleted.', 'success')
    return redirect(url_for('admin_library'))

# --- ADMIN FINANCIAL REPORTS ---
def _get_finance_data():
    ledger = []
    
    paid_fees = list(fees_collection.find({'status': 'Paid'}))
    for f in paid_fees:
        date_str = f.get('paid_on', f.get('created_at').strftime('%Y-%m-%d') if f.get('created_at') else '')
        ledger.append({
            'date': date_str,
            'description': f"Fee Payment: {f.get('description', '')}",
            'type': 'Income',
            'amount': f.get('amount', 0)
        })
        
    paid_salaries = list(salaries_collection.find({'status': 'Paid'}))
    for s in paid_salaries:
        date_str = s.get('created_at').strftime('%Y-%m-%d') if s.get('created_at') else ''
        ledger.append({
            'date': date_str,
            'description': f"Salary Payment for {s.get('month', '')}",
            'type': 'Expense',
            'amount': s.get('amount', 0)
        })
        
    all_expenses = list(expenses_collection.find())
    for e in all_expenses:
        ledger.append({
            'date': e.get('date', e.get('created_at').strftime('%Y-%m-%d') if e.get('created_at') else ''),
            'description': f"Expense: {e.get('description', '')}",
            'type': 'Expense',
            'amount': e.get('amount', 0)
        })
        
    ledger.sort(key=lambda x: x['date'] if x['date'] else '', reverse=True)
    
    from collections import defaultdict
    monthly_data = defaultdict(lambda: {'income': 0, 'expense': 0})
    yearly_data = defaultdict(lambda: {'income': 0, 'expense': 0})
    
    for item in ledger:
        date_str = item['date']
        if not date_str:
            continue
            
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            month_key = dt.strftime('%Y-%m')
            year_key = dt.strftime('%Y')
        except:
            month_key = date_str[:7]
            year_key = date_str[:4]
            
        if item['type'] == 'Income':
            monthly_data[month_key]['income'] += item['amount']
            yearly_data[year_key]['income'] += item['amount']
        else:
            monthly_data[month_key]['expense'] += item['amount']
            yearly_data[year_key]['expense'] += item['amount']
            
    for m in monthly_data:
        monthly_data[m]['net'] = monthly_data[m]['income'] - monthly_data[m]['expense']
    for y in yearly_data:
        yearly_data[y]['net'] = yearly_data[y]['income'] - yearly_data[y]['expense']
        
    monthly_stmt = [{'period': k, **v} for k, v in sorted(monthly_data.items(), reverse=True)]
    yearly_stmt = [{'period': k, **v} for k, v in sorted(yearly_data.items(), reverse=True)]
    
    total_income = sum(item['amount'] for item in ledger if item['type'] == 'Income')
    total_expense = sum(item['amount'] for item in ledger if item['type'] == 'Expense')
    cash = total_income - total_expense
    
    infrastructure_items = list(infrastructure_collection.find())
    infrastructure_value = sum(item.get('value', 0) for item in infrastructure_items)
    
    total_assets = cash + infrastructure_value
    
    unpaid_salaries = list(salaries_collection.find({'status': 'Pending'}))
    total_liabilities = sum(s.get('amount', 0) for s in unpaid_salaries)
    
    equity = total_assets - total_liabilities
    
    balance_sheet = {
        'assets': [
            {'name': 'Cash Equivalent', 'amount': cash},
            {'name': 'Infrastructure Value', 'amount': infrastructure_value}
        ],
        'total_assets': total_assets,
        'liabilities': [
            {'name': 'Pending Salaries', 'amount': total_liabilities}
        ],
        'total_liabilities': total_liabilities,
        'equity': equity,
        'total_liabilities_equity': total_liabilities + equity
    }
    
    return ledger, monthly_stmt, yearly_stmt, balance_sheet

@app.route('/admin/finance')
@login_required
@role_required('admin')
def admin_finance():
    ledger, monthly_stmt, yearly_stmt, balance_sheet = _get_finance_data()
    return render_template('finance_reports.html', 
                           ledger=ledger, 
                           monthly_stmt=monthly_stmt, 
                           yearly_stmt=yearly_stmt, 
                           balance_sheet=balance_sheet)

@app.route('/admin/finance/download/income_statement')
@login_required
@role_required('admin')
def download_income_statement():
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    _, monthly_stmt, yearly_stmt, _ = _get_finance_data()
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, 750, "Smart Student System - Income Statement")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 710, "Monthly Profit & Loss")
    
    y = 680
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Period")
    c.drawString(150, y, "Income")
    c.drawString(250, y, "Expense")
    c.drawString(350, y, "Net Income")
    
    y -= 20
    c.setFont("Helvetica", 10)
    for m in monthly_stmt:
        if y < 100:
            c.showPage()
            y = 750
        c.drawString(50, y, m['period'])
        c.drawString(150, y, f"${m['income']:.2f}")
        c.drawString(250, y, f"${m['expense']:.2f}")
        c.drawString(350, y, f"${m['net']:.2f}")
        y -= 20
        
    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='Income_Statement.pdf', mimetype='application/pdf')

@app.route('/admin/finance/download/balance_sheet')
@login_required
@role_required('admin')
def download_balance_sheet():
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    _, _, _, balance_sheet = _get_finance_data()
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, 750, "Smart Student System - Balance Sheet")
    
    y = 700
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Assets")
    y -= 25
    c.setFont("Helvetica", 12)
    for a in balance_sheet['assets']:
        c.drawString(70, y, f"{a['name']}: ${a['amount']:.2f}")
        y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Total Assets: ${balance_sheet['total_assets']:.2f}")
    
    y -= 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Liabilities")
    y -= 25
    c.setFont("Helvetica", 12)
    for l in balance_sheet['liabilities']:
        c.drawString(70, y, f"{l['name']}: ${l['amount']:.2f}")
        y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Total Liabilities: ${balance_sheet['total_liabilities']:.2f}")
    
    y -= 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Equity")
    y -= 25
    c.setFont("Helvetica", 12)
    c.drawString(70, y, f"Retained Earnings / Net Position: ${balance_sheet['equity']:.2f}")
    
    y -= 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"Total Liabilities & Equity: ${balance_sheet['total_liabilities_equity']:.2f}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='Balance_Sheet.pdf', mimetype='application/pdf')

@app.route('/admin/finance/download/ledger')
@login_required
@role_required('admin')
def download_ledger():
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    ledger, _, _, _ = _get_finance_data()
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, 750, "Smart Student System - General Ledger")
    
    y = 700
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Date")
    c.drawString(150, y, "Description")
    c.drawString(450, y, "Type")
    c.drawString(520, y, "Amount")
    
    y -= 20
    c.setFont("Helvetica", 10)
    for item in ledger:
        if y < 100:
            c.showPage()
            y = 750
        c.drawString(50, y, item['date'])
        c.drawString(150, y, item['description'][:50] + ('...' if len(item['description']) > 50 else ''))
        c.drawString(450, y, item['type'])
        c.drawString(520, y, f"${item['amount']:.2f}")
        y -= 20
        
    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='General_Ledger.pdf', mimetype='application/pdf')

# --- STUDENT ROUTES ---
@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    student_id = session.get('user_id')
    student = students_collection.find_one({'_id': ObjectId(student_id)})
    
    total_classes = attendance_collection.count_documents({'student_id': student_id})
    present_classes = attendance_collection.count_documents({'student_id': student_id, 'status': 'Present'})
    absent_classes = attendance_collection.count_documents({'student_id': student_id, 'status': 'Absent'})
    
    attendance_perc = 0
    if total_classes > 0:
        attendance_perc = round((present_classes / total_classes) * 100, 1)
        
    history = list(attendance_collection.find({'student_id': student_id}).sort('date', -1).limit(5))
    
    return render_template('student_dashboard.html', 
                          student=student, 
                          attendance_perc=attendance_perc,
                          present_classes=present_classes,
                          absent_classes=absent_classes,
                          total_classes=total_classes,
                          history=history)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_profile():
    student_id = session.get('user_id')
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        roll = request.form.get('roll')
        department = request.form.get('department')
        contact = request.form.get('contact', '')
        
        update_fields = {
            'name': name,
            'email': email,
            'roll': roll,
            'department': department,
            'contact': contact
        }
        
        if 'picture' in request.files:
            pic = request.files['picture']
            if pic.filename != '':
                filename = secure_filename(pic.filename)
                pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                update_fields['picture'] = filename
        
        students_collection.update_one(
            {'_id': ObjectId(student_id)},
            {'$set': update_fields}
        )
        users_collection.update_one(
            {'_id': ObjectId(student_id)},
            {'$set': {
                'username': name,
                'email': email
            }}
        )
        
        session['username'] = name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student_profile'))
        
    student = students_collection.find_one({'_id': ObjectId(student_id)})
    return render_template('profile.html', student=student)

@app.route('/student/report/download')
@login_required
@role_required('student')
def download_report():
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    student_id = session.get('user_id')
    student = students_collection.find_one({'_id': ObjectId(student_id)})
    
    total = attendance_collection.count_documents({'student_id': student_id})
    present = attendance_collection.count_documents({'student_id': student_id, 'status': 'Present'})
    
    perc = 0
    if total > 0:
        perc = round((present / total) * 100, 1)
        
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, 750, "Smart Student System - Attendance Report")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, 700, f"Student Name: {student.get('name', '')}")
    c.drawString(50, 680, f"Roll Number: {student.get('roll', '')}")
    c.drawString(50, 660, f"Department: {student.get('department', '')}")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 620, "Attendance Summary")
    c.setFont("Helvetica", 12)
    c.drawString(50, 595, f"Total Classes: {total}")
    c.drawString(50, 575, f"Classes Attended: {present}")
    c.drawString(50, 555, f"Attendance Percentage: {perc}%")
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'Attendance_Report_{student.get("name","")}.pdf', mimetype='application/pdf')

# --- STUDENT FEE MANAGEMENT ---
@app.route('/student/fees')
@login_required
@role_required('student')
def student_fees():
    student_id = session.get('user_id')
    fees = list(fees_collection.find({'student_id': student_id}).sort('created_at', -1))
    
    total_due = sum(f['amount'] for f in fees if f.get('status') == 'Pending')
    total_paid = sum(f['amount'] for f in fees if f.get('status') == 'Paid')
    
    return render_template('student_fees.html', fees=fees, total_due=total_due, total_paid=total_paid)

@app.route('/student/fee/pay/<fee_id>', methods=['POST'])
@login_required
@role_required('student')
def pay_fee(fee_id):
    method = request.form.get('payment_method')
    fees_collection.update_one(
        {'_id': ObjectId(fee_id)}, 
        {'$set': {
            'status': 'Paid', 
            'payment_method': method,
            'paid_on': datetime.now().strftime('%Y-%m-%d')
        }}
    )
    flash(f'Payment successful via {method}!', 'success')
    return redirect(url_for('student_fees'))

@app.route('/student/fee/installment/<fee_id>', methods=['POST'])
@login_required
@role_required('student')
def apply_installment(fee_id):
    fee = fees_collection.find_one({'_id': ObjectId(fee_id)})
    if not fee or fee.get('status') == 'Paid':
        flash('Invalid fee or already paid.', 'danger')
        return redirect(url_for('student_fees'))
        
    amount = float(fee.get('amount', 0))
    half_amount = amount / 2.0
    
    try:
        current_due = datetime.strptime(fee.get('due_date'), '%Y-%m-%d')
    except:
        current_due = datetime.now()
        
    next_due = (current_due + timedelta(days=30)).strftime('%Y-%m-%d')
    
    fees_collection.insert_one({
        'student_id': fee['student_id'],
        'amount': half_amount,
        'description': fee.get('description') + ' (Installment 1/2)',
        'due_date': fee.get('due_date'),
        'status': 'Pending',
        'created_at': datetime.now()
    })
    
    fees_collection.insert_one({
        'student_id': fee['student_id'],
        'amount': half_amount,
        'description': fee.get('description') + ' (Installment 2/2)',
        'due_date': next_due,
        'status': 'Pending',
        'created_at': datetime.now()
    })
    
    fees_collection.delete_one({'_id': ObjectId(fee_id)})
    
    flash('Fee successfully split into installments!', 'success')
    return redirect(url_for('student_fees'))

@app.route('/fee/voucher/<fee_id>')
@login_required
def generate_fee_voucher(fee_id):
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    fee = fees_collection.find_one({'_id': ObjectId(fee_id)})
    if not fee:
        flash('Fee not found', 'danger')
        return redirect(url_for('index'))
        
    role = session.get('role')
    user_id = session.get('user_id')
    
    if role == 'student' and str(fee.get('student_id')) != str(user_id):
        flash('Unauthorized', 'danger')
        return redirect(url_for('student_fees'))
        
    student = students_collection.find_one({'_id': ObjectId(fee['student_id'])})
    bank_setting = settings_collection.find_one({'key': 'bank_account'})
    bank_account = bank_setting['value'] if bank_setting else 'Not Configured (Contact Auth)'
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, 750, "Smart Student System - Official Fee Voucher")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, 700, f"Student Name: {student.get('name', 'N/A')}")
    c.drawString(50, 680, f"Roll Number: {student.get('roll', 'N/A')}")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 640, "Fee Details")
    c.setFont("Helvetica", 12)
    c.drawString(50, 615, f"Description: {fee.get('description', '')}")
    c.drawString(50, 595, f"Amount Due: ${'%.2f' % fee.get('amount', 0)}")
    c.drawString(50, 575, f"Due Date: {fee.get('due_date', '')}")
    c.drawString(50, 555, f"Status: {fee.get('status', 'Pending')}")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 500, "Payment Instructions")
    c.setFont("Helvetica", 12)
    c.drawString(50, 475, "Please deposit the amount to the following bank account:")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 455, f"Account Number: {bank_account}")
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'Fee_Voucher_{student.get("roll","")}.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
