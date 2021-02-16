from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()

POSTGRES = {
    'user': 'postgres',
    'pw': 'qp1337',
    'db': 'postgres',
    'host': 'db',
    'port': '5432',
}

def create_app():
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
    app.config['DEBUG'] = True
    # change this:
    app.config['SECRET_KEY'] = b'\xc6\xf7O\xe0\xc3\xf9.\x8cX^\xbe\xddc+\xd1\xf78I\xac<h*\x91S\xf2\x04(|Z|\xb3G>\xa9b\xfe\xc1\x16\x05\n\xcc\x15\x9b\xd0\xfa\xc2\xce\xd69>&\x8e\x182\xc0\x16\xf1\xd7\xff\x05u\xd1\xc3g'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES

    db.init_app(app)
    
    with app.app_context():
        try:
            db.engine.execute("""
                CREATE TABLE IF NOT EXISTS Users (
                    id serial PRIMARY KEY,
                    name VARCHAR ( 50 ) UNIQUE NOT NULL,
                    email VARCHAR ( 100) UNIQUE NOT NULL,
                    password VARCHAR ( 100 ) NOT NULL
                );

                CREATE TABLE IF NOT EXISTS Posts (
                    post_id serial PRIMARY KEY,
                    user_id serial REFERENCES Users(id),
                    urn text UNIQUE NOT NULL,
                    date timestamp NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS Followers (
                    follower_id serial REFERENCES Users(id),
                    following_id serial REFERENCES Users(id),
                    PRIMARY KEY (follower_id, following_id)
                );

                CREATE TABLE IF NOT EXISTS Likes (
                    user_id serial REFERENCES Users(id),
                    post_id serial REFERENCES Posts(post_id),
                    PRIMARY KEY (user_id, post_id)
                );
            """)
        except Exception as e:
            print('Database connection error - ', e)
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import Users

    @login_manager.user_loader
    def load_user(id):
        # since the id is just the primary key of our user table, use it in the query for the user
        return Users.query.get(int(id))

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # blueprint for rest api
    from .rest import rest as rest_blueprint
    app.register_blueprint(rest_blueprint)

    return app