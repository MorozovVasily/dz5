from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from . import db
import boto3
import base64

session3 = boto3.session.Session()
s3 = session3.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net'
)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)

@main.route('/trending')
def trending():
    print("trending AAA")
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
        my_list = []
        for row in rows:
            print(row[2])
            row[2] = base64.b64encode(s3.get_object(Bucket='my-object-storage', Key=row[2])['Body'].read()).decode('utf-8')
            my_list.append(row)
        print(len(my_list))
        print(my_list)
        return render_template('trending.html',  results=my_list)
    except Exception as e:
        print(e)
        return redirect(url_for('main.index'))

@main.route('/users')
def users():
    try:
        rows = db.engine.execute("""
            SELECT name, count(posts.post_id) post_count, u.id FROM 
            (SELECT * FROM Users) AS u
            LEFT JOIN Posts ON Posts.user_id = u.id
            GROUP BY Posts.user_id, name, id ORDER BY post_count DESC LIMIT 100;
        """)
        my_list = []
        for row in rows:
            my_list.append(row)
        return render_template('users.html',  results=my_list)
    except Exception as e:
        print(e)
        return redirect(url_for('main.index'))