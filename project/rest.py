from flask import Blueprint, render_template, redirect, Response, url_for, request, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from .models import Users
from . import db
import os
from os import makedirs
from werkzeug.utils import secure_filename
import imghdr
import json

rest = Blueprint('rest', __name__)

@rest.route('/api/trending')
def trending():
    try:
        rows = db.engine.execute("""
            SELECT name, date, urn, l.liked, l.like_count, ps.post_id
            FROM
                (SELECT * FROM Users) AS u
                JOIN
				(
					SELECT *
                 	FROM Posts
				 	WHERE date >= NOW() -  INTERVAL '24 HOURS'
				) AS ps
                ON
                    u.id = ps.user_id
                LEFT JOIN
                    (
                        SELECT post_id, array_agg(name) as liked, count(Likes.user_id) like_count
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
                    ps.post_id = l.post_id
            WHERE l.like_count IS NOT NULL
            ORDER BY l.like_count DESC
            LIMIT 10;
        """)
        trending = list(rows)
        data = {'trending': trending}
        resp = Response(json.dumps(data, indent=4, sort_keys=True, default=str), status=200, mimetype="application/json")
        return resp
    except Exception as e:
        print(e)
        return []

@rest.route('/api/create_user', methods=['POST'])
def create_user():
    try:
        content = request.json
        rows = db.engine.execute("""
            INSERT INTO Users(name, email, password) VALUES(%s, %s, %s) RETURNING id;
            """, content['name'], content['email'], content['password'])
        id = list(rows)
        data = {'id': id[0][0]}
        resp = Response(json.dumps(data, indent=4, sort_keys=True, default=str), status=200, mimetype="application/json")
        return resp
    except Exception as e:
        print(e)
        return []

@rest.route('/api/new_post', methods=['POST'])
def new_post():
    try:
        content = request.json
        rows = db.engine.execute("""
            INSERT INTO Posts(user_id, urn) VALUES(%s, %s) RETURNING post_id;
            """, content['user_id'], content['urn'])
        post_id = list(rows)
        data = {'post_id': post_id[0][0]}
        resp = Response(json.dumps(data, indent=4, sort_keys=True, default=str), status=200, mimetype="application/json")
        return resp
    except Exception as e:
        print(e)
        return []

@rest.route('/api/like', methods=['POST'])
def like():
    try:
        content = request.json
        rows = db.engine.execute("""
            INSERT INTO Likes(user_id, post_id) VALUES(%s, %s);
            """, content['user_id'], content['post_id'])
        data = {}
        resp = Response(json.dumps(data, indent=4, sort_keys=True, default=str), status=200, mimetype="application/json")
        return resp
    except Exception as e:
        print(e)
        return []

@rest.route('/api/follow', methods=['POST'])
def follow():
    try:
        content = request.json
        rows = db.engine.execute("""
            INSERT INTO Followers(follower_id, following_id) VALUES(%s, %s);
            """, content['follower_id'], content['following_id'])
        data = {}
        resp = Response(json.dumps(data, indent=4, sort_keys=True, default=str), status=200, mimetype="application/json")
        return resp
    except Exception as e:
        print(e)
        return []

@rest.route('/api/users', methods=['GET'])
def users():
    try:
        rows = db.engine.execute("""
            SELECT name, count(posts.post_id) post_count FROM 
            (SELECT * FROM Users) AS u
            LEFT JOIN Posts ON Posts.user_id = u.id
            GROUP BY Posts.user_id, name ORDER BY post_count DESC LIMIT 100;
        """)
        users = list(rows)
        data = {'users': users}
        resp = Response(json.dumps(data, indent=4, sort_keys=True, default=str), status=200, mimetype="application/json")
        return resp
    except Exception as e:
        return []

@rest.route('/api/user/<username>', methods=['GET', 'POST'])
def profile(username):
    try:
        rows = db.engine.execute("""
            SELECT name, date, urn, l.liked
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
        """
        )
        user = list(rows)
        data = {'user': user}
        resp = Response(json.dumps(data, indent=4, sort_keys=True, default=str), status=200, mimetype="application/json")
        return resp
    except Exception as e:
        print(e)
        return []

@rest.route('/api/feed')
def feed():
    try:
        content = request.json
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
        """, content['user_id'])
        feed = list(rows)
        data = {'feed': feed}
        resp = Response(json.dumps(data, indent=4, sort_keys=True, default=str), status=200, mimetype="application/json")
        return resp
    except Exception as e:
        print(e)
        return []

def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + format

@rest.route('/api/uploader', methods = ['GET', 'POST'])
def uploader():
    if request.method == 'POST':
        UPLOAD_EXTENSIONS = ['.jpg', '.png', '.jpeg', '.bmp']
        APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/img')

        uploaded_file = request.files['file']
        filename = secure_filename(uploaded_file.filename)
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in UPLOAD_EXTENSIONS or \
                    validate_image(uploaded_file.stream) is None:
                return "Invalid image", 400

        uploaded_file.save(os.path.join(UPLOAD_FOLDER, filename))
    return 'file uploaded successfully'

