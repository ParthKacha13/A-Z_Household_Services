from flask import Flask,render_template,request,redirect,url_for,flash,session,jsonify  
from sqlalchemy import and_
from app import app
from models import db,User,Service,ServiceProfessional,ServiceRequest,Customer,Review,RejectedRequest
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import date,datetime
from functools import wraps

# --Login--
def login_required(fun):
    @wraps(fun)
    def func(*args,**kwargs):
        if 'user_id' in session:
            return fun(*args,**kwargs)
        else:
            flash("Login to continue")
            return redirect(url_for('login'))
    return func

def login_admin(fun):   
    @wraps(fun)
    def func_a(*args,**kwargs):
        if 'user_id' not in session:
            flash("Login to continue")
            return redirect(url_for('login'))
        user=User.query.get(session['user_id'])
        if not user.is_admin:
            if user.role=='Customer':
                flash("You are not Admin!")
                return redirect(url_for('home_c'))
            else:
                flash("You are not Admin!")
                return redirect(url_for('home_p'))
        return fun(*args,**kwargs)
    return func_a

def login_prosessional(fun):
    @wraps(fun)
    def func_p(*args,**kwargs):
        if 'user_id' not in session:
            flash("Login to continue")
            return redirect(url_for('login'))
        user=User.query.get(session['user_id'])
        if not user.role=='Serviceprofessional':
            if user.role=='Customer':
                flash("You are not Service Professional!")
                return redirect(url_for('home_c'))
            else:
                return redirect(url_for('home_a'))
        return fun(*args,**kwargs)
    return func_p

def is_blocked(fun):
    @wraps(fun)
    def func_b(*args,**kwargs):
        user=User.query.get(session['user_id'])
        if user and user.is_blocked:
            return redirect(url_for('block'))
        return fun(*args,**kwargs)
    return func_b

def login_customer(fun):
    @wraps(fun)
    def func_c(*args,**kwargs):
        if 'user_id' not in session:
            flash("Login to continue")
            return redirect(url_for('login'))
        user=User.query.get(session['user_id'])
        if not user.role=='Customer':
            if user.role=='Serviceprofessional':
                flash("You are not Customer!")
                return redirect(url_for('home_p'))
            else:
                return redirect(url_for('home_a'))
        return fun(*args,**kwargs)
    return func_c

@app.route('/block',methods=['GET','POST'])
def block():
    if request.method=='POST':
        action=request.form.get('action')
        if action=='back':
            return redirect(url_for('login'))
    return render_template('block.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='GET':
        return render_template('login.html')
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        
        user=User.query.filter_by(email=email).first()

        if user and check_password_hash(user.passhash,password) and user.is_admin==False and user.role=='Customer':
            if user.is_blocked:
                return redirect(url_for('block'))
            session['user_id']=user.id
            flash('Login Successfull !')
            return redirect(url_for('home_c'))
        elif user and check_password_hash(user.passhash,password) and user.is_admin==False and user.role=='Serviceprofessional' :
            if user.is_blocked:
                return redirect(url_for('block'))
            session['user_id']=user.id
            flash('Login Successfull !')
            return redirect(url_for('home_p'))
        elif user and check_password_hash(user.passhash,password) and user.is_admin==True:
            session['user_id']=user.id
            flash('Login Successfull !')
            return redirect(url_for('home_a'))
        else:
            flash("Invalid email or password")
            return redirect(url_for('login'))


# --Logout--
@app.route('/logout')
@login_required
def logout():
    session.pop('user_id')
    return redirect(url_for('homepage'))


# --Admin--

# @app.route('/', methods=['GET'])
# def homepage():
#     if request.method=='GET':
#         return render_template('homepage.html')
@app.route('/')
def homepage():
    return render_template('homepage.html')


@app.route('/home_a')
@login_admin
def home_a():
    user_session=User.query.get(session['user_id'])
    professionals = ServiceProfessional.query.outerjoin(User).all()
    user=User.query.get(session['user_id'])
    customers = Customer.query.outerjoin(User).all()
    services=Service.query.all()
    service_requests=ServiceRequest.query.all()

    return render_template('home_a.html',professionals=professionals,user_session=user_session,user=user,services=services,service_requests=service_requests,customers=customers)

@app.route('/rating-data')
def rating_data():
    closed_requests = ServiceRequest.query.filter_by(service_status='Closed').all()

    rating_counts = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0, 'Not Rated': 0}
    for request in closed_requests:
        rating = str(request.service_rating) if request.service_rating else 'Not Rated'
        if rating in rating_counts:
            rating_counts[rating] += 1

    data = {
        'labels': list(rating_counts.keys()),
        'data': list(rating_counts.values())
    }

    return jsonify(data)

@app.route('/servicereq-data')
def servicereq_data():
    service_requests = ServiceRequest.query.all()
    requests = {'Requested': 0, 'Accepted': 0, 'Closed': 0, 'Rejected': 0}

    for request in service_requests:
        if request.service_status in requests:
            requests[request.service_status] += 1

    data = {
        'labels': list(requests.keys()),
        'data': list(requests.values())
    }
    return jsonify(data)

@app.route('/new_service',methods=['GET','POST'])
@login_admin
def new_service():
    if request.method=='GET':
        user_session=User.query.get(session['user_id'])
        return render_template('new_service.html',user_session=user_session)
    else:
        service_name=request.form.get('service_name')
        description=request.form.get('description')
        base_price=request.form.get('base_price')
        time_required=request.form.get('time_required')
        if not service_name or not base_price or not time_required:
            flash('Please fill out all fields')
            return redirect(url_for('new_service'))
        
        new_service=Service(name=service_name,description=description,base_price=base_price,time_required=time_required)
        db.session.add(new_service)
        db.session.commit()

        flash('Service added successfully!')
        return redirect(url_for('home_a'))

@app.route('/edit_service/<int:id>',methods=['GET','POST'])
@login_admin
def edit_new_service(id):
    if request.method=='GET':
        edit_service=Service.query.get(id)
        if not edit_service:
            return(redirect(url_for('home_a')))
        return render_template('edit_service.html',service=edit_service)
    else:
        edit_service=Service.query.get(id)
        if not edit_service:
            return(redirect(url_for('home_a')))
        service_name=request.form.get('service_name')
        description=request.form.get('description')
        base_price=request.form.get('base_price')
        time_required=request.form.get('time_required')

        if service_name:
            edit_service.name=service_name
        if time_required:
            edit_service.time_required=time_required
        if description:
            edit_service.description=description
        if base_price:
            edit_service.base_price=base_price
        db.session.commit()
        flash('Service edited!')
        return redirect(url_for('home_a'))

@app.route('/delete_service/<int:id>',methods=['POST'])
@login_admin
def delete_service(id):
    service=Service.query.get(id)
    if not service:
        flash('Service not available')
        return redirect(url_for('home_a'))
    action=request.form.get('action')
    if action=='delete':
        professionals = ServiceProfessional.query.filter_by(service_id=id).all()
        for professional in professionals:
            professional.service_id = None
            professional.service_name = "Service not selected"
            professional.professional_status = "Pending"
        db.session.commit()
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted')
    
    return redirect(url_for('home_a'))

@app.route('/service_profile/<int:professional_id>')
@login_admin
def service_profile(professional_id):
    user_session=User.query.get(session['user_id'])
    professional = ServiceProfessional.query.get((professional_id))
    user=User.query.get(professional.user_id)
    return render_template('service_profile.html',professional=professional,user=user,user_session=user_session)

@app.route('/update_customer_status/<int:id>',methods=['POST'])
@login_admin
def update_customer_status(id):
    customer=Customer.query.get(id)
    if not customer:
        flash('Customer not found')
        return redirect(url_for('home_a'))
    user=customer.user
    action=request.form.get('action')
    if action=='block':
        if user:
            user.is_blocked=True
            db.session.commit()
    elif action=='unblock':
        if user:
            user.is_blocked=False
            db.session.commit()
    else:
        flash('Invalid action')
        return redirect(url_for('home_a'))
    flash(f"Professional has been {action}ed")
    return redirect(url_for('home_a'))

@app.route('/update_professional_status/<int:id>',methods=['POST'])
@login_admin
def update_professional_status(id):
        professional = ServiceProfessional.query.get(id)
        if not professional:
            flash('Professional not found')
            return redirect(url_for('home_a'))
        user=professional.user
        action=request.form.get('action')
        if action=='accept':
            professional.professional_status='Approved'
        elif action=='reject':
            professional.professional_status='Rejected'
        elif action=='block':
            if user:
                user.is_blocked=True
                professional.professional_status='Blocked'
                db.session.commit()
        elif action == 'unblock': 
            if user:
                user.is_blocked = False
                professional.professional_status = 'Pending'
                db.session.commit()
        else:
            flash('Invalid action')
            return redirect(url_for('home_a'))
        
        db.session.commit()
        flash(f"Professional has been {action}ed")
        return redirect(url_for('home_a'))

@app.route('/search_a', methods=['GET', 'POST'])
@login_admin
def search_a():
    user_session=User.query.get(session['user_id']) 
    service_requests = []
    professionals = []
    services = []
    customers = []
    services_baseprice = []
    services_time = []
    customers_address = []
    customers_pincode = []
    professionals_service = []
    professionals_experience = []
    professionals_status = []
    professionals_address = []
    search_word = ""
    search_by = ""


    if request.method == 'POST':
        search_by = request.form.get('search_by')
        search_word = request.form.get('search')
        if search_by == 'Service Name':
            services = Service.query.filter(Service.name.like(f'%{search_word}%')).all()   
            if search_word.isdigit():
                base_price = int(search_word)
                services_baseprice = Service.query.filter(Service.base_price == base_price).all()
                time_required = int(search_word)
                services_time = Service.query.filter(Service.time_required == time_required).all()
            else:
                services_baseprice = []
                services_time = []
        elif search_by == 'Customer':
            customers = Customer.query.join(User).filter(User.full_name==search_word).all()
            customers_address = Customer.query.join(User).filter(User.address.ilike(f'%{search_word}%')).all()
            if search_word.isdigit():
                pincode = int(search_word)
                customers_pincode = Customer.query.join(User).filter(User.pincode==pincode).all()
            else:
                customers_pincode = []
        elif search_by == 'Professional':
            professionals = ServiceProfessional.query.join(User).filter(User.full_name==search_word).all()
            professionals_service = ServiceProfessional.query.join(Service).filter(Service.name.like(f'%{search_word}%')).all()
            if search_word.isdigit():
                experience = int(search_word)
                professionals_experience = ServiceProfessional.query.filter(ServiceProfessional.experience == experience).all()
            else:
                professionals_experience = []
            professionals_address = ServiceProfessional.query.join(User).filter(User.address.ilike(f'%{search_word}%')).all()
            professionals_status = ServiceProfessional.query.filter(ServiceProfessional.professional_status==search_word).all()
        elif search_by == 'Service Status':
            service_requests = ServiceRequest.query.filter(ServiceRequest.service_status==search_word).all()
            
        return render_template('search_a.html',user_session=user_session,service_requests=service_requests,
            professionals=professionals,services=services,customers=customers,search=search_word,search_by=search_by,
            services_baseprice=services_baseprice,services_time=services_time,customers_address=customers_address,
            customers_pincode=customers_pincode,professionals_service=professionals_service,professionals_experience=professionals_experience,professionals_status=professionals_status,professionals_address=professionals_address)
    return render_template(
        'search_a.html', user_session=user_session, service_requests=service_requests,
        professionals=professionals, services=services, customers=customers
    )

@app.route('/summary/admin')
@login_admin
def summary_admin():
    user_session=User.query.get(session['user_id'])
    customers = Customer.query.all()
    professionals = ServiceProfessional.query.all()
    services = Service.query.all()
    service_requests = ServiceRequest.query.all()
    return render_template('summary_admin.html',user_session=user_session,customers=customers,professionals=professionals,services=services,service_requests=service_requests)


#  --Customer--  

@app.route('/customer_signup',methods=['GET','POST'])
def customer_signup():
    if request.method=='GET':
        return render_template('customer_signup.html')
    else:
        email=request.form.get('email')
        password=request.form.get('password')
        fullname=request.form.get('fullname')
        address=request.form.get('address')
        pincode=request.form.get('pincode')

        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for('customer_signup'))
        
        password_hash=generate_password_hash(password)

        new_user=User(email=email,passhash=password_hash,full_name=fullname,address=address,pincode=pincode,role="Customer",is_admin=False)
        db.session.add(new_user)
        db.session.commit()

        new_customer=Customer(user_id=new_user.id)
        db.session.add(new_customer)
        db.session.commit()
        flash('You have successfully registered. Please login to continue.')

        return redirect(url_for('login'))

@app.route('/profile_customer')
@login_customer
@is_blocked
def profile_customer():
    user=User.query.get(session['user_id'])
    user_session=User.query.get(session['user_id'])
    return render_template('profile_customer.html',user=user,user_session=user_session)

@app.route('/edit_customer',methods=['GET','POST'])
@login_customer
@is_blocked
def edit_customer():
    if request.method=='GET':
        user=User.query.get(session['user_id'])
        user_session=User.query.get(session['user_id'])
        return render_template('edit_customer.html',user=user,user_session=user_session)
    else:
        email=request.form.get('email')
        password=request.form.get('password')
        fullname=request.form.get('fullname')
        address=request.form.get('address')
        pincode=request.form.get('pincode')

        user=User.query.get(session['user_id'])

        if not email or not password:
            flash('Please fill required fields')
            return redirect(url_for('edit_customer'))
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            flash("Email already exists")
            return redirect(url_for('edit_customer'))
        
        new_pass_hash=generate_password_hash(password)

        user.email=email
        user.passhash=new_pass_hash
        if fullname:
            user.full_name=fullname
        if address:    
            user.address=address
        if pincode:
            user.pincode=pincode
        db.session.commit()
        flash('Profile updated !')
        return redirect(url_for('profile_customer'))

@app.route('/home_c')
@login_customer
@is_blocked
def home_c():
    users=User.query.get(session['user_id'])
    user_session=User.query.get(session['user_id'])
    services=Service.query.all()
    customer = Customer.query.filter_by(user_id=session['user_id']).first()
    service_history = ServiceRequest.query.filter_by(customer_id=customer.id).all() 
    service_professionals = ServiceProfessional.query.join(User).filter(ServiceProfessional.professional_status == 'Approved')
    return render_template('home_c.html',user_session=user_session,users=users,services=services,service_history=service_history,service_professionals=service_professionals)

@app.route('/customer-chart')
def customer_chart():
        user=User.query.get(session['user_id'])
        service_requests = ServiceRequest.query.filter_by(customer_id=user.customer.id).all()
        requests = {'Requested': 0, 'Accepted': 0, 'Closed': 0, 'Rejected':0}

        for request in service_requests:
            if request.service_status in requests:
                requests[request.service_status] += 1

        data = {
            'labels': list(requests.keys()),
            'data': list(requests.values())
        }
        return jsonify(data)

@app.route('/request_service/<int:service_id>', methods=['GET', 'POST'])
@login_customer
@is_blocked
def request_service(service_id):
    user_session=User.query.get(session['user_id'])
    customer_id =Customer.query.filter_by(user_id=session['user_id']).first()
    user=User.query.get(session['user_id'])
    if not customer_id:
        flash("You must be logged in to request a service.")
        return redirect(url_for('login'))

    professional = ServiceProfessional.query.filter_by(service_id=service_id, professional_status='Approved').all()
    
    if not professional:
        flash("No service professional is assigned or approved for this service.")
        return redirect(url_for('home_c'))
    
    professional_id = None

    if request.method=='POST':
        service = Service.query.get(service_id)
        if not service:
            flash("Service not found.")
            return redirect(url_for('home_c'))
        
        professional_id = request.form.get('profname')

        selected_professional = ServiceProfessional.query.filter_by(service_id=service_id, professional_status='Approved', user_id=User.query.filter_by(full_name=professional_id).first().id).first()
        if not selected_professional:
            flash("Service professional not found or not approved.")
            return redirect(url_for('home_c'))
        
        new_request = ServiceRequest(service_id=service.id,  customer_id=customer_id.id,professional_id=selected_professional.id if selected_professional else None)
        db.session.add(new_request)
        db.session.commit()
        flash("Service requested successfully!")
        return redirect(url_for('home_c'))
    
    service = Service.query.get(service_id)
    if not service:
        flash("Service not found.")
        return redirect(url_for('home_c'))

    return render_template('request_service.html',user=user,user_session=user_session,professional_id=professional_id ,service=service,professional=professional)


@app.route('/close_service/<int:service_request_id>', methods=['POST'])
@login_customer
@is_blocked
def close_service(service_request_id):
    service_request = ServiceRequest.query.get(service_request_id)
    
    if service_request.service_status=='Closed':
        flash('Service request closed already')
        return redirect(url_for('home_c'))
    if service_request.service_status=='Rejected':
        flash('Service request rejected')
        return redirect(url_for('home_c'))
    if service_request.service_status=='Requested':
        flash('Service request is not accepted yet')
        return redirect(url_for('home_c'))
    if service_request.service_status=='Completed':
        service_request.service_status = 'Closed'
        service_request.date_of_completion = datetime.now()
        db.session.commit()
        flash('Service request closed successfully')
    else:
        flash('Service is not completed yet')
        return redirect(url_for('home_c'))

    return redirect(url_for('home_c'))

@app.route('/cancel_service/<int:service_request_id>', methods=['POST'])
@login_customer
@is_blocked
def cancel_service(service_request_id):
    service_request = ServiceRequest.query.get(service_request_id)
    customer = Customer.query.filter_by(user_id=session['user_id']).first()
    if service_request and service_request.customer_id == customer.id:
        db.session.delete(service_request)
        db.session.commit()
        flash("Service request canceled successfully")
    else:
        flash("Service request not found or unauthorized action")
    return redirect(url_for('home_c'))

def update_avg_rating(professional_id):
    reviews = Review.query.join(ServiceRequest).filter(ServiceRequest.professional_id == professional_id).all()
    if reviews:
        avg_rating = sum(review.rating for review in reviews) / len(reviews)
    else:
        avg_rating = 0
    professional = ServiceProfessional.query.get(professional_id)
    if professional:
        professional.avg_rating = avg_rating
        db.session.commit()

@app.route('/review_service/<int:service_request_id>', methods=['GET', 'POST'])
@login_customer
@is_blocked
def review_service(service_request_id):
    user_session=User.query.get(session['user_id'])
    service=Service.query.join(ServiceRequest).filter(ServiceRequest.id==service_request_id).first()
    if not service:
        flash('Service not found')
        return redirect(url_for('home_c'))
    service_request = ServiceRequest.query.get(service_request_id)
    if not service_request:
        flash('Service request not found')
        return redirect(url_for('home_c'))
    
    if service_request.service_status == 'Closed':
        flash('Service is closed')
        return redirect(url_for('home_c'))
    elif service_request.service_status == 'Rejected':
        flash('Service is rejected')
        return redirect(url_for('home_c'))
    elif service_request.service_status == 'Requested':
        flash('Service is not accepted yet')
        return redirect(url_for('home_c'))
    elif service_request.service_status == 'Accepted':
        flash('Service is not completed yet')
        return redirect(url_for('home_c'))
    
    existing_review = Review.query.filter_by(service_request_id=service_request_id).first()
    if existing_review:
        flash('Rating already done')
        return redirect(url_for('home_c'))
    
    if request.method == 'POST':
        if service_request.service_status=='Completed':
            if existing_review:
                flash('Rating already done')
                return redirect(url_for('home_c'))
            else:
                rating = request.form.get('rating')
                comment = request.form.get('comment')
                if not rating:
                    flash('Rating is required')
                    return redirect(url_for('review_service', service_request_id=service_request_id))
                review = Review(service_request_id=service_request_id, rating=rating, comment=comment)
                db.session.add(review)
                service_request.service_rating = rating
                db.session.commit()
                flash('Review added successfully')
                
                service_request = ServiceRequest.query.get(service_request_id)
                if service_request and service_request.professional_id:
                    update_avg_rating(service_request.professional_id)

                return redirect(url_for('home_c', service_request_id=service_request_id))
        else:
            return redirect(url_for('home_c'))

    return render_template('review_service.html',user_session=user_session ,service_request=service_request,servicename=service.name)

@app.route('/search_c', methods=['GET', 'POST'])
@login_customer
@is_blocked
def search_c():
    user=User.query.get(session['user_id'])
    user_session=User.query.get(session['user_id'])
    customer=Customer.query.filter_by(user_id=session['user_id']).first()
    service_name=[]
    service_address=[]
    service_pincode=[]
    service=[]
    service_price = []
    search_word = ""
    search_by = ""

    if request.method=='POST':
        search_by=request.form.get('search_by')
        search_word=request.form.get('search')

        if search_by=="Service Name":
            service_name=Service.query.filter(Service.name.ilike(f'%{search_word}%')).all()
        
        elif search_by=="Price":
            try:
                price=int(search_word)
                service_price=Service.query.filter(Service.base_price==price).all()
            except ValueError:
                flash('Invalid price')
                return redirect(url_for('search_c'))

        elif search_by=="Address":
            service_address=ServiceProfessional.query.join(User).filter(User.address.ilike(f'%{search_word}%')).all()
            
        elif search_by=="Pincode":
            try:
                pincode=int(search_word)
                service_pincode=ServiceProfessional.query.join(User).filter(User.pincode==pincode).all()
            except ValueError:
                flash('Invalid pincode')
                return redirect(url_for('search_c'))
            
        return render_template('search_c.html',customer=customer,user=user,user_session=user_session,service=service,search=search_word,search_by=search_by,service_name=service_name,service_pincode=service_pincode,service_address=service_address,service_price=service_price)
    return render_template('search_c.html',customer=customer,user=user,user_session=user_session,service=service,search=search_word,search_by=search_by,service_name=service_name,service_pincode=service_pincode,service_address=service_address,service_price=service_price)


@app.route('/summary/customer')
@login_customer
@is_blocked
def summary_customer():
    user_session=User.query.get(session['user_id'])
    customers = Customer.query.all()
    professionals = ServiceProfessional.query.all()
    services = Service.query.all()
    service_requests = ServiceRequest.query.all()
    return render_template('summary_customer.html',user_session=user_session,customers=customers,professionals=professionals,services=services,service_requests=service_requests)


# --Professional--

@app.route('/service_professional_signup',methods=['GET','POST'])
def service_professional_signup():
    if request.method=='GET':
        services = Service.query.all() 
        return render_template('service_professional_signup.html',services=services)
    else:
        email=request.form.get('email')
        password=request.form.get('password')
        full_name=request.form.get('fullname')
        service_name=request.form.get('servicename')
        experience=request.form.get('experience')
        add=request.form.get('address')
        pincode=request.form.get('pincode')

        if not email or not password or not full_name or not service_name or not experience or not add or not pincode:
            flash('Please fill out all fields')
            return redirect(url_for('service_professional_signup'))
        
        user=User.query.filter_by(email=email).first()

        if user:
            flash("Username already exists")
            return redirect(url_for("service_professional_signup"))
        
        password_hash=generate_password_hash(password)

        new_user=User(email=email,passhash=password_hash,full_name=full_name,address=add,pincode=pincode,role="Serviceprofessional",is_admin=False)

        db.session.add(new_user)
        db.session.commit()
    
        service = Service.query.filter_by(name=service_name).first()
        if service:
            new_professional = ServiceProfessional(user_id=new_user.id, service_id=service.id, experience=experience, service_name=service.name)
            db.session.add(new_professional)
            db.session.commit()
            flash('You have successfully registered. Please login to continue.')
            return (redirect(url_for('login'))) 

@app.route('/profile_service')
@login_prosessional
@is_blocked
def profile_service():
    user=User.query.get(session['user_id'])
    user_session=User.query.get(session['user_id'])
    service_professional = ServiceProfessional.query.filter_by(user_id=user.id).first()
    return render_template('profile_service.html',user=user,service_professional=service_professional,user_session=user_session)

@app.route('/home_p')
@login_prosessional
@is_blocked
def home_p():
    user=User.query.get(session['user_id'])
    if not user:
        flash("User not found")
    today = date.today()
    user_session=User.query.get(session['user_id'])
    service_requests_t = ServiceRequest.query.filter_by(professional_id=user.professional.id).filter(ServiceRequest.date_of_request >= today).all()
    service_requests_p = ServiceRequest.query.filter_by(professional_id=user.professional.id).filter(ServiceRequest.date_of_request < today).all()
    service_requests = ServiceRequest.query.filter_by(professional_id=user.professional.id).all()
    
    customers_t = {}
    for request in service_requests_t:
        customer = Customer.query.get(request.customer_id)
        if customer:
            customers_t[request.id] = customer
    customers_p = {}
    for request in service_requests_p:
        customer = Customer.query.get(request.customer_id)
        if customer:
            customers_p[request.id] = customer
    customers = {}
    for request in service_requests:
        customer = Customer.query.get(request.customer_id)
        if customer:
            customers[request.id] = customer

    professional = ServiceProfessional.query.filter_by(user_id=user.id).first()
    return render_template('home_p.html',user=user,user_session=user_session, professional=professional,service_requests=service_requests,service_requests_p=service_requests_p ,service_requests_t=service_requests_t,customers=customers,customers_p=customers_p ,customers_t=customers_t)

@app.route('/personal-rating')
def personal_rating():
    user=User.query.get(session['user_id'])
    service_requests = ServiceRequest.query.filter_by(professional_id=user.professional.id,service_status='Closed').all()

    rating_counts = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0, 'Not Rated': 0}
    for request in service_requests:
        rating = str(request.service_rating) if request.service_rating else 'Not Rated'
        if rating in rating_counts:
            rating_counts[rating] += 1

    data = {
        'labels': list(rating_counts.keys()),
        'data': list(rating_counts.values())
    }

    return jsonify(data)

@app.route('/service-status-data')
def service_status_data():
    user=User.query.get(session['user_id'])
    service_requests = ServiceRequest.query.filter_by(professional_id=user.professional.id).all()
    requests = {'Requested': 0, 'Accepted': 0, 'Closed': 0, 'Rejected': 0}

    for request in service_requests:
        if request.service_status in requests:
            requests[request.service_status] += 1

    data = {
        'labels': list(requests.keys()),
        'data': list(requests.values())
    }

    return jsonify(data)

@app.route('/edit_professional',methods=['GET','POST'])
@login_prosessional
@is_blocked
def edit_professional():
    if request.method=='GET':
        user=User.query.get(session['user_id'])
        service_professional = ServiceProfessional.query.filter_by(user_id=user.id).first()
        services = Service.query.all()
        user_session=User.query.get(session['user_id'])
        return render_template('edit_professional.html',user=user,user_session=user_session,professional=service_professional, services=services)
    else:
        email=request.form.get('email')
        password=request.form.get('password')
        full_name=request.form.get('fullname')
        service_name=request.form.get('servicename')
        experience=request.form.get('experience')
        add=request.form.get('address')
        pincode=request.form.get('pincode')

        user=User.query.get(session['user_id'])
        service_professional = ServiceProfessional.query.filter_by(user_id=user.id).first()
        
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            flash("Email already exists")
            return redirect(url_for('edit_professional'))
        
        if not email or not password:
            flash('Please fill required fields')
            return redirect(url_for('edit_professional'))
            
        if service_name:
            service = Service.query.filter_by(name=service_name).first()
            if service:
                service_professional.service_id = service.id  
                service_professional.service_name = service_name
                service_professional.professional_status='Pending'
                db.session.commit()

        new_pass_hash=generate_password_hash(password)

        user.email=email 
        user.passhash=new_pass_hash

        if full_name:
            user.full_name=full_name 
        if experience:
            service_professional.experience=experience     
        if add:    
            user.address=add
        if pincode:
            user.pincode=pincode
        
        db.session.commit()
        flash('Profile updated !')
        return redirect(url_for('profile_service'))

@app.route('/view_customer/<int:request_id>')
@login_prosessional
@is_blocked
def view_customer(request_id):
    user_session=User.query.get(session['user_id'])
    service_request = ServiceRequest.query.get(request_id)
    if not service_request:
        flash("Service request not found.")
        return redirect(url_for('home_p'))
    
    customer=Customer.query.join(User).filter(Customer.id == service_request.customer_id).first()
    if not customer:
        flash("Customer not found.")
        return redirect(url_for('home_p'))

    return render_template('view_customer.html', customer=customer,user_session=user_session)

@app.route('/update_request_status/<int:request_id>', methods=['POST'])
@login_prosessional
@is_blocked
def update_request_status(request_id):
    service_request = ServiceRequest.query.get(request_id)
    professional = ServiceProfessional.query.filter_by(user_id=session['user_id']).first()
    if service_request.professional_id != professional.id:
        flash("You are not authorized to update this request.")
        return redirect(url_for('home_p'))

    action = request.form.get('action')
    if action == 'Accept':
        service_request.service_status = 'Accepted'
    elif action == 'Reject':
        service_request.service_status = 'Rejected'
        r_request = RejectedRequest(service_request_id=service_request.id, professional_id=professional.id)
        db.session.add(r_request)
    else:
        flash("Invalid action.")
        return redirect(url_for('home_p'))
    
    db.session.commit()
    flash(f"Request has been {action}ed.")
    return redirect(url_for('home_p'))

@app.route('/complete_service/<int:request_id>', methods=['POST'])
@login_prosessional
@is_blocked
def complete_service(request_id):
    service_request = ServiceRequest.query.get(request_id)
    professional = ServiceProfessional.query.filter_by(user_id=session['user_id']).first()
    if service_request.professional_id != professional.id:
        flash("You are not authorized to update this request.")
        return redirect(url_for('home_p'))

    action = request.form.get('action')
    if service_request.service_status != 'Accepted':
        flash("Service request is not accepted yet.")
        return redirect(url_for('home_p'))
    elif action == 'complete':
        service_request.service_status = 'Completed'
    else:
        flash("Invalid action.")
        return redirect(url_for('home_p'))
    
    db.session.commit()
    flash(f"Service has been successfully completed.")
    return redirect(url_for('home_p'))

@app.route('/search_p', methods=['GET', 'POST'])
@login_prosessional
@is_blocked
def search_p():
    user=User.query.get(session['user_id'])
    user_session=User.query.get(session['user_id'])
    service_requests = []
    professional = ServiceProfessional.query.filter_by(user_id=user.id).first()
    search_word = ""
    search_by = ""

    if request.method=='POST':
        search_by = request.form.get('search_by')
        search_word = request.form.get('search')    

        if search_by == 'Address':
            service_requests = (ServiceRequest.query.join(ServiceRequest.customer).join(Customer.user).filter(and_(User.address.ilike(f'%{search_word}%'),ServiceRequest.professional_id == professional.id)).all())
        elif search_by == 'Pincode':
            try:
                pincode = int(search_word)
                service_requests = (ServiceRequest.query.join(ServiceRequest.customer).join(Customer.user).filter(and_(User.pincode == pincode,ServiceRequest.professional_id == professional.id)).all())
            except ValueError:
                flash('Invalid pincode')
                return redirect(url_for('search_p'))
        elif search_by == 'Service_Status':
            service_requests = (ServiceRequest.query.filter(and_(ServiceRequest.service_status == search_word,ServiceRequest.professional_id == professional.id)).all())
        return (render_template('search_p.html',user_session=user_session,search=search_word,search_by=search_by,service_requests=service_requests,professional=professional,user=user))
    return render_template('search_p.html',user_session=user_session,search=search_word,search_by=search_by,service_requests=service_requests,professional=professional,user=user)  

@app.route('/summary/professional')
@login_prosessional
@is_blocked
def summary_professional():
    user_session=User.query.get(session['user_id'])
    customers = Customer.query.all()
    professionals = ServiceProfessional.query.all()
    services = Service.query.all()
    service_requests = ServiceRequest.query.all()
    return render_template('summary_professional.html',user_session=user_session,customers=customers,professionals=professionals,services=services,service_requests=service_requests)