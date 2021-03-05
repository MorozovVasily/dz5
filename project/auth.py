from flask import Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, Response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from .models import Users
from . import db
import os
from os import makedirs
from werkzeug.utils import secure_filename
import imghdr
import boto3
import base64
import sys

session3 = boto3.session.Session()
s3 = session3.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net'
)

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = Users.query.filter_by(email=email).first()

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login')) # if the user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)
    return redirect(url_for('main.profile'))

@auth.route('/signup')
def signup():
    return render_template('signup.html')

@auth.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    user = Users.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash('Email address already exists')
        return redirect(url_for('auth.signup'))

    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    new_user = Users(email=email, name=name, password=generate_password_hash(password, method='sha256'))

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth.login'))

@auth.route('/user/<username>')
@login_required
def user(username):
    try:
        rows = db.engine.execute("""
            SELECT name, date, urn, l.liked, Posts.post_id, u.id
            FROM
                (
                SELECT
                    id, name
                FROM
                    Users
                WHERE name = '""" + username + """'
                )
                AS u
                JOIN
                    Posts
                ON
                    u.id = Posts.user_id
                LEFT JOIN
                    (
                        SELECT post_id, array_agg(name) as liked
                        FROM
                            Likes
                        JOIN
                            Users
                        ON
                            Users.id = Likes.user_id
                        GROUP BY
                            post_id
                    ) AS l
                ON
                    Posts.post_id = l.post_id
            ORDER BY date DESC
            LIMIT 10;
        """)
        response = ''
        my_list = []
        for row in rows:
            my_list.append(row)
        return render_template('user.html',  results=my_list, name=username)
    except Exception as e:
        print(e)
        return redirect(url_for('main.index'))

@auth.route('/like/<post_id>', methods=['GET', 'POST'])
@login_required
def like(post_id):
    try:
        content = request.json
        rows = db.engine.execute("""
            INSERT INTO Likes(user_id, post_id) VALUES(%s, %s) ON CONFLICT DO NOTHING;
            """, current_user.id, post_id)
        data = {}
        return redirect(url_for('main.index'))
    except Exception as e:
        print(e)
        return []

@auth.route('/follow/<following_id>', methods=['GET', 'POST'])
@login_required
def follow(following_id):
    try:
        content = request.json
        rows = db.engine.execute("""
            INSERT INTO Followers(follower_id, following_id) VALUES(%s, %s) ON CONFLICT DO NOTHING;
            """, current_user.id, following_id)
        data = {}
        return redirect(url_for('main.index'))
    except Exception as e:
        print(e)
        return []

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth.route('/feed')
@login_required
def feed():
    try:
        rows = db.engine.execute("""
            SELECT name, date, urn, l.liked, Posts.post_id
            FROM
                (
                SELECT
                    following_id
                FROM
                    Followers
                WHERE
                    follower_id = %s
                ) AS follow
                JOIN
                    Posts
                ON
                    follow.following_id = Posts.user_id
                JOIN
                    Users
                ON
                    Posts.user_id = Users.id
                LEFT JOIN
                    (
                        SELECT post_id, array_agg(name) as liked
                        FROM
                            Likes
                        JOIN
                            Users
                        ON
                            Users.id = Likes.user_id
                        GROUP BY
                            post_id
                    ) AS l
                ON
                    Posts.post_id = l.post_id
            ORDER BY date DESC
            LIMIT 10;
        """, current_user.id)
        response = ''
        my_list = []
        d = []
        for row in rows:
            # print(row[2], file=sys.stderr)
            try:
                dz = base64.b64encode(s3.get_object(Bucket='my-object-storage', Key=row[2])['Body'].read()).decode('utf-8')
                # print(dz, file=sys.stderr)
                d.append(dz)
                # print()
                my_list.append(row)
            except Exception as e:
                print(e, file=sys.stderr)
        return render_template('feed.html',  results=my_list, data=d)
    except Exception as e:
        print(e, file=sys.stderr)
        return redirect(url_for('main.index'))

def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + format

@auth.route('/upload')
@login_required
def upload():
   return render_template('upload.html')

@auth.route('/uploader', methods = ['POST'])
@login_required
def uploader():
    if request.method == 'POST':
        UPLOAD_EXTENSIONS = ['.jpg', '.png', '.jpeg', '.bmp']
        APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/img')

        try:
            uploaded_file = request.files['file']
            filename = secure_filename(uploaded_file.filename)
            if filename != '':
                file_ext = os.path.splitext(filename)[1]
                if file_ext not in UPLOAD_EXTENSIONS or \
                        validate_image(uploaded_file.stream) is None:
                    return "Invalid image", 400
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            print("AAA OK")
            s3.put_object(Bucket='my-object-storage', Key=filename, Body=uploaded_file.read())
            print("AAA2 OK")

            uploaded_file.save(os.path.join(UPLOAD_FOLDER, filename))

            rows = db.engine.execute("INSERT INTO Posts (user_id, urn) VALUES (" + str(current_user.id) + ", '" + filename + "');")
            return redirect(url_for('main.index'))
        except Exception as e:
            print(e)
            return redirect(url_for('main.index'))

    return redirect(url_for('main.index'))