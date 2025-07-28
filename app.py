from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from functools import wraps
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tabaro3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Add a function to get the current user
def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# Make the function available to all templates
@app.context_processor
def utility_processor():
    return dict(get_current_user=get_current_user)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    blood_type = db.Column(db.String(5), nullable=False)
    city = db.Column(db.String(50), nullable=False)  # الولاية
    district = db.Column(db.String(50), nullable=True)  # الدائرة
    is_donor = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

class BloodRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blood_type = db.Column(db.String(5), nullable=False)
    units_needed = db.Column(db.Integer, nullable=False)
    hospital = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)  # Changed back to city to match database
    contact_phone = db.Column(db.String(20), nullable=False)
    details = db.Column(db.Text, nullable=True)
    is_urgent = db.Column(db.Boolean, default=False)
    is_fulfilled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    requester = db.relationship('User', backref=db.backref('blood_requests', lazy=True))
    
    def __repr__(self):
        return f'<BloodRequest {self.id}>'

# Routes
@app.route('/')
def home():
    urgent_requests = BloodRequest.query.filter_by(is_urgent=True, is_fulfilled=False).order_by(BloodRequest.created_at.desc()).limit(5).all()
    recent_requests = BloodRequest.query.filter_by(is_fulfilled=False).order_by(BloodRequest.created_at.desc()).limit(10).all()
    return render_template('index.html', urgent_requests=urgent_requests, recent_requests=recent_requests)

# تعديل وظيفة التسجيل لاستخدام أسماء الولايات كما هي في ملف algeria_cities.js
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        blood_type = request.form.get('blood_type')
        state = request.form.get('state')  # الولاية بالتنسيق "01 - أدرار"
        city = request.form.get('city')  # الدائرة
        is_donor = 'is_donor' in request.form
        
        # التحقق من وجود المستخدم
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash('اسم المستخدم أو البريد الإلكتروني موجود بالفعل.')
            return redirect(url_for('register'))
        
        # إنشاء مستخدم جديد
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            full_name=full_name,
            phone=phone,
            blood_type=blood_type,
            city=state,  # حفظ الولاية كاملة
            district=city,  # حفظ الدائرة
            is_donor=is_donor
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('تم التسجيل بنجاح! يرجى تسجيل الدخول.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# تعديل وظيفة البحث لاستخدام أسماء الولايات كما هي في ملف algeria_cities.js
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        blood_type = request.form.get('blood_type')
        state = request.form.get('state')  # الولاية بالتنسيق "01 - أدرار"
        city = request.form.get('city')  # الدائرة
        
        query = User.query.filter_by(is_donor=True)
        
        if blood_type:
            query = query.filter_by(blood_type=blood_type)
        if state:
            query = query.filter_by(city=state)  # البحث باستخدام الولاية كاملة
        if city:
            query = query.filter_by(district=city)  # البحث باستخدام الدائرة
        
        donors = query.all()
        return render_template('search_results.html', donors=donors)
    
    return render_template('search.html')

# تعديل وظيفة طلب الدم لاستخدام أسماء الولايات كما هي في ملف algeria_cities.js
@app.route('/request_blood', methods=['GET', 'POST'])
def request_blood():
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول لطلب الدم.')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        blood_type = request.form.get('blood_type')
        units_needed = request.form.get('units_needed')
        hospital = request.form.get('hospital')
        state = request.form.get('state')  # الولاية بالتنسيق "01 - أدرار"
        city = request.form.get('city')  # الدائرة
        contact_phone = request.form.get('contact_phone')
        details = request.form.get('details')
        is_urgent = 'is_urgent' in request.form
        
        new_request = BloodRequest(
            requester_id=session['user_id'],
            blood_type=blood_type,
            units_needed=units_needed,
            hospital=hospital,
            city=state,  # حفظ الولاية كاملة
            contact_phone=contact_phone,
            details=details,
            is_urgent=is_urgent
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        flash('تم إرسال طلب الدم بنجاح!')
        return redirect(url_for('dashboard'))
    
    return render_template('request_blood.html')

# تعديل وظيفة تعديل الملف الشخصي لاستخدام أسماء الولايات كما هي في ملف algeria_cities.js
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول للوصول إلى هذه الصفحة.')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        # تحديث بيانات المستخدم
        user.full_name = request.form.get('full_name')
        user.phone = request.form.get('phone')
        user.blood_type = request.form.get('blood_type')
        user.city = request.form.get('state')  # الولاية بالتنسيق "01 - أدرار"
        user.district = request.form.get('city')  # الدائرة
        user.is_donor = 'is_donor' in request.form
        
        # تحديث كلمة المرور إذا تم إدخالها
        new_password = request.form.get('password')
        if new_password:
            user.password = generate_password_hash(new_password)
        
        db.session.commit()
        flash('تم تحديث البيانات بنجاح!')
        return redirect(url_for('dashboard'))
    
    # نحذف قائمة الولايات الثابتة ونعتمد على ملف algeria_cities.js
    # لأن الملف يحتوي على الولايات بالتنسيق "01 - أدرار"
    
    return render_template('edit_profile.html', user=user)

@app.route('/requests')
def all_requests():
    requests = BloodRequest.query.filter_by(is_fulfilled=False).order_by(BloodRequest.created_at.desc()).all()
    return render_template('all_requests.html', requests=requests)

@app.route('/request/<int:request_id>')
def view_request(request_id):
    blood_request = BloodRequest.query.get_or_404(request_id)
    return render_template('view_request.html', request=blood_request)

@app.route('/mark_fulfilled/<int:request_id>')
def mark_fulfilled(request_id):
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول لتنفيذ هذا الإجراء.')
        return redirect(url_for('login'))
    
    blood_request = BloodRequest.query.get_or_404(request_id)
    
    if blood_request.requester_id != session['user_id']:
        flash('غير مصرح لك بتنفيذ هذا الإجراء.')
        return redirect(url_for('dashboard'))
    
    blood_request.is_fulfilled = True
    db.session.commit()
    
    flash('تم تحديث الطلب كمكتمل!')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('يرجى تسجيل الدخول للوصول إلى لوحة التحكم.')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    # Add a check to ensure user exists
    if user is None:
        flash('حدث خطأ في العثور على حسابك. يرجى تسجيل الدخول مرة أخرى.')
        session.pop('user_id', None)  # Clear the invalid session
        return redirect(url_for('login'))
        
    user_requests = BloodRequest.query.filter_by(requester_id=user.id).order_by(BloodRequest.created_at.desc()).all()
    
    return render_template('dashboard.html', user=user, requests=user_requests)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('تم تسجيل الدخول بنجاح!')
            return redirect(url_for('dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('تم تسجيل الخروج بنجاح.')
    return redirect(url_for('home'))

# إضافة مسار للتحقق من صلاحيات المسؤول
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('يرجى تسجيل الدخول أولاً')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('ليس لديك صلاحية الوصول إلى هذه الصفحة')
            return redirect(url_for('home'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    # إضافة منطق التحقق من المستخدم الحالي إذا كان مسؤولاً
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user is None or not user.is_admin:
            flash('غير مصرح لك بالوصول إلى هذه الصفحة')
            return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        
        # التحقق من إدخال جميع البيانات المطلوبة
        if not username or not email or not password or not confirm_password or not full_name or not phone:
            flash('يرجى ملء جميع الحقول المطلوبة')
            return render_template('admin/create_admin.html')
        
        # التحقق من تطابق كلمات المرور
        if password != confirm_password:
            flash('كلمات المرور غير متطابقة')
            return render_template('admin/create_admin.html')
        
        # التحقق من وجود المستخدم بشكل منفصل
        username_exists = User.query.filter_by(username=username).first()
        if username_exists:
            flash('اسم المستخدم موجود بالفعل، يرجى اختيار اسم مستخدم آخر')
            return render_template('admin/create_admin.html', 
                                  email=email, 
                                  full_name=full_name, 
                                  phone=phone)
            
        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            flash('البريد الإلكتروني موجود بالفعل، يرجى استخدام بريد إلكتروني آخر')
            return render_template('admin/create_admin.html', 
                                  username=username, 
                                  full_name=full_name, 
                                  phone=phone)
        
        try:
            # إنشاء مستخدم مسؤول جديد
            new_admin = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                full_name=full_name,
                phone=phone,
                is_admin=True,
                is_donor=False,
                blood_type='N/A',
                city='N/A',
                district='N/A',
                created_at=datetime.utcnow()  # تحديد وقت الإنشاء بشكل صريح
            )
            
            db.session.add(new_admin)
            db.session.commit()
            flash('تم إنشاء حساب المسؤول بنجاح')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إنشاء الحساب: {str(e)}')
            print(f"Error creating admin: {str(e)}")  # للتشخيص
            return render_template('admin/create_admin.html')
    
    return render_template('admin/create_admin.html')

# Add this after your create_admin route

# Add this to your imports at the top
from sqlalchemy import desc

# Add this model class with your other models
class DonorReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)
    report_details = db.Column(db.Text, nullable=False)
    reporter_name = db.Column(db.String(100))
    reporter_contact = db.Column(db.String(100))
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    donor = db.relationship('User', backref=db.backref('reports', lazy=True))

# Add this route to handle reports
@app.route('/report_donor/<int:donor_id>', methods=['POST'])
def report_donor(donor_id):
    donor = User.query.get_or_404(donor_id)
    
    report_type = request.form.get('report_type')
    report_details = request.form.get('report_details')
    reporter_name = request.form.get('reporter_name', '')
    reporter_contact = request.form.get('reporter_contact', '')
    
    # Create new report
    new_report = DonorReport(
        donor_id=donor.id,
        report_type=report_type,
        report_details=report_details,
        reporter_name=reporter_name,
        reporter_contact=reporter_contact
    )
    
    try:
        db.session.add(new_report)
        db.session.commit()
        flash('تم إرسال البلاغ بنجاح. سيتم مراجعته من قبل الإدارة.')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء إرسال البلاغ: {str(e)}')
    
    return redirect(url_for('search'))

# Modify the admin_dashboard route to include reports
@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    # Get all users
    users = User.query.all()
    # Get all blood requests
    blood_requests = BloodRequest.query.order_by(BloodRequest.created_at.desc()).all()
    # Get all reports
    reports = DonorReport.query.order_by(desc(DonorReport.created_at)).all()
    
    return render_template('admin/dashboard.html', users=users, requests=blood_requests, reports=reports)

# Add a route to mark reports as resolved
@app.route('/admin/resolve_report/<int:report_id>')
@admin_required
def resolve_report(report_id):
    report = DonorReport.query.get_or_404(report_id)
    report.is_resolved = True
    
    try:
        db.session.commit()
        flash('تم تحديث حالة البلاغ بنجاح')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء تحديث حالة البلاغ: {str(e)}')
    
    return redirect(url_for('admin_dashboard'))

# Remove this line - it's a duplicate return statement outside any function
# return redirect(url_for('admin_dashboard'))

# Blood request management routes
@app.route('/admin/edit_request/<int:request_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_request(request_id):
    blood_request = BloodRequest.query.get_or_404(request_id)
    
    if request.method == 'POST':
        blood_request.blood_type = request.form.get('blood_type')
        blood_request.units_needed = request.form.get('units_needed')
        blood_request.hospital = request.form.get('hospital')
        blood_request.city = request.form.get('state')
        blood_request.contact_phone = request.form.get('contact_phone')
        blood_request.details = request.form.get('details')
        blood_request.is_urgent = 'is_urgent' in request.form
        blood_request.is_fulfilled = 'is_fulfilled' in request.form
        
        try:
            db.session.commit()
            flash('تم تحديث طلب الدم بنجاح')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث الطلب: {str(e)}')
    
    return render_template('admin/edit_request.html', request=blood_request)

@app.route('/admin/delete_request/<int:request_id>')
@admin_required
def admin_delete_request(request_id):
    blood_request = BloodRequest.query.get_or_404(request_id)
    
    try:
        db.session.delete(blood_request)
        db.session.commit()
        flash('تم حذف طلب الدم بنجاح')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف الطلب: {str(e)}')
    
    return redirect(url_for('admin_dashboard'))

# Admin user management routes
@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        # Update user data
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.full_name = request.form.get('full_name')
        user.phone = request.form.get('phone')
        user.blood_type = request.form.get('blood_type')
        user.city = request.form.get('state')
        user.district = request.form.get('city')
        user.is_donor = 'is_donor' in request.form
        user.is_admin = 'is_admin' in request.form
        
        # Update password if provided
        new_password = request.form.get('password')
        if new_password:
            user.password = generate_password_hash(new_password)
        
        try:
            db.session.commit()
            flash('تم تحديث بيانات المستخدم بنجاح')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث البيانات: {str(e)}')
    
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Cannot delete current user
    if user.id == session['user_id']:
        flash('لا يمكنك حذف حسابك الحالي')
        return redirect(url_for('admin_dashboard'))
    
    try:
        # Delete associated blood requests first
        BloodRequest.query.filter_by(requester_id=user.id).delete()
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        flash('تم حذف المستخدم بنجاح')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف المستخدم: {str(e)}')
    
    return redirect(url_for('admin_dashboard'))

# تعديل الجزء الأخير من الملف
if __name__ == '__main__':
    # إنشاء قاعدة البيانات إذا لم تكن موجودة
    with app.app_context():
        db.create_all()
        
        # Create an initial admin user if none exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin_user = User(
                username='admin',
                email='admin@tabaro3.com',
                password=generate_password_hash('admin123'),
                full_name='مدير النظام',
                phone='0000000000',
                is_admin=True,
                is_donor=False,
                blood_type='N/A',
                city='N/A',
                district='N/A'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("تم إنشاء حساب المدير بنجاح!")
            print("اسم المستخدم: admin")
            print("كلمة المرور: admin123")
    
    # تشغيل التطبيق
    app.run(debug=True, host='0.0.0.0')

# تأكد من أن المتغير app متاح للوصول إليه من wfastcgi
# لا تقم بتغيير اسم المتغير app لأن IIS سيبحث عنه

# إضافة دعم Firebase Functions
from firebase_functions import https_fn

@https_fn.on_request()
def app_function(request):
    with app.app_context():
        db.create_all()
        # التحقق من وجود مستخدم مسؤول
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin_user = User(
                username='admin',
                email='admin@tabaro3.com',
                password=generate_password_hash('admin123'),
                full_name='مدير النظام',
                phone='0000000000',
                is_admin=True,
                is_donor=False,
                blood_type='N/A',
                city='N/A',
                district='N/A'
            )
            db.session.add(admin_user)
            db.session.commit()
    
    return app(request)
