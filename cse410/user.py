from flask_login import UserMixin
import sqlite3
from uuid import uuid4
import bcrypt

from util import hash, sql_to_dict, test_password

columns = ["uid", "username", "password"]

conn = sqlite3.connect("users.sqlite", autocommit=True, check_same_thread=False)
def sql(query, params=None):
    if params is None:
        params = ()
    cur = conn.cursor()
    data = cur.execute(query, params).fetchall()
    cur.close()
    return data
    
sql("CREATE TABLE IF NOT EXISTS Users (uid varchar(36), username varchar(255), password varchar(255))")

# learn how to make custom context
def get_users():
    return sql("SELECT * FROM Users")
def create_new_user(username, password):
    sql("INSERT INTO Users (uid, username, password) VALUES (?, ?, ?)", (str(uuid4()), username, hash(password)))


class User(UserMixin):
    def __init__(self, uid, username, password):
        self.id = uid
        self.username = username
        self.password = password

    @staticmethod
    def attempt_authentication(username, password):
        user = __class__.get_by_username(username)
        if not user:
            return None
        if test_password(password, user.password):
            return user

    @staticmethod
    def get(user_id):
        user = sql("SELECT * FROM Users WHERE uid = ?", (user_id,))
        if user:
            return User(user[0][0], user[0][1], user[0][2])
        return None
    
    @staticmethod
    def get_by_username(username):
        user = sql("SELECT * FROM Users WHERE username = ?", (username))
        if user:
            return User(user[0][0], user[0][1], user[0][2])
        return None