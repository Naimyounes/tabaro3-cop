class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    blood_type = db.Column(db.String(5), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    is_donor = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)  # إضافة حقل المسؤول
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات مع الجداول الأخرى
    blood_requests = db.relationship('BloodRequest', backref='requester', lazy=True)