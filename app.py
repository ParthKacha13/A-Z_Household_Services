# from flask import Flask,render_template
# app = Flask(__name__)

# import config

# import models

# import controllers

# if __name__  == '__main__':
#     app.run(debug=True)


# ------

from flask import Flask
import config
from models import db

app = Flask(__name__)

# Load config
app.config.from_object(config)

# Init DB
db.init_app(app)

# Import controllers AFTER app is ready
import controllers

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)
    with app.app_context():
        db.create_all()

        # Create admin if not exists
        from models import User
        from werkzeug.security import generate_password_hash

        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            admin = User(
                email='admin@gmail.com',
                passhash=generate_password_hash('admin'),
                full_name='admin',
                address='india',
                pincode='000000',
                role='admin',
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)
