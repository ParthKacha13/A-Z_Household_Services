# from app import app
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash

# db=SQLAlchemy(app)
db=SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(75),unique=True,nullable=False)
    passhash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(75), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)
    role = db.Column(db.String(20), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)

class Service(db.Model):
    __tablename__ = 'service'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(75), nullable=True)
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Float, nullable=False)
    time_required = db.Column(db.Integer, nullable=True)

    requests = db.relationship('ServiceRequest', backref='service', cascade='save-update, merge')
    service_professionals = db.relationship('ServiceProfessional', backref='service', cascade='save-update, merge')


class ServiceProfessional(db.Model):
    __tablename__ = 'service_professional'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id',ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', onupdate='CASCADE'), nullable=True)
    experience = db.Column(db.Integer, nullable=False)
    service_name = db.Column(db.String(100), nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    professional_status = db.Column(db.String(20), default='Pending')
    avg_rating = db.Column(db.Float, nullable=True,default=0)

    user = db.relationship('User', backref=db.backref('professional', uselist=False), cascade="all,delete")


class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    date_joined = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref=db.backref('customer', uselist=False))

class ServiceRequest(db.Model):
    __tablename__='service_request' 
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', onupdate='CASCADE'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    professional_id = db.Column(db.Integer, db.ForeignKey('service_professional.id', onupdate='CASCADE'), nullable=True)
    date_of_request = db.Column(db.DateTime, default=datetime.now)
    date_of_completion = db.Column(db.DateTime, nullable=True)
    service_status = db.Column(db.String(20), default='Requested')  
    service_rating = db.Column(db.Integer, nullable=True)

    customer = db.relationship('Customer', backref='service_requests')
    professional = db.relationship('ServiceProfessional', backref='service_requests', cascade='save-update, merge')

class Review(db.Model):
    __tablename__ = 'review'
    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('service_request.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) 
    comment = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.now)

    service_request = db.relationship('ServiceRequest', backref=db.backref('review', cascade="all, delete"))

class RejectedRequest(db.Model):
    __tablename__ = 'rejected_request'
    
    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('service_request.id',onupdate='CASCADE'), nullable=True)
    professional_id = db.Column(db.Integer, db.ForeignKey('service_professional.id',onupdate='CASCADE'), nullable=True)
    
    service_request = db.relationship('ServiceRequest', backref='rejected_by', lazy=True,cascade='save-update, merge')
    professional = db.relationship('ServiceProfessional', backref='rejected_request', lazy=True,cascade='save-update, merge')

# with app.app_context():
#     db.create_all()
    
#     admin=User.query.filter_by(is_admin=True).first()
    
#     if not admin:
#         password_hash=generate_password_hash('admin')
#         admin=User(email='admin@gmail.com',passhash=password_hash,full_name='admin',address='india',pincode=0,role='admin',is_admin=True)
#         db.session.add(admin)
#         db.session.commit()