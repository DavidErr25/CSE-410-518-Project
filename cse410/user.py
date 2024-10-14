from flask_login import UserMixin
import sqlite3
from uuid import uuid4
import bcrypt
from friends import friends_of, is_open_invite, accept_friendship, new_friendship

from util import hash, sql_to_dict, test_password

conn = sqlite3.connect("users.sqlite", check_same_thread=False)
def sql(query, params=None):
    if params is None:
        params = ()
    cur = conn.cursor()
    data = cur.execute(query, params).fetchall()
    conn.commit()
    cur.close()
    return data
    
columns = ["uid", "username", "password"]
sql("CREATE TABLE IF NOT EXISTS Users (uid varchar(36), username varchar(255), password varchar(255))")

def create_new_user(username, password):
    uuid = str(uuid4())
    sql("INSERT INTO Users (uid, username, password) VALUES (?, ?, ?)", (uuid, username, hash(password)))
    return uuid


class User(UserMixin):
    def __init__(self, uid, username, password):
        self.id = uid
        self.username = username
        self.password = password

    def get_friends(self, ):
        return friends_of(self.id)
    
    def add_friend(self, other):
        other_id = User.get_by_username(other).id
        # Check if already friends
        if other_id in self.get_friends():
            return False
        
        # Check for pending request (outgoing)
        if is_open_invite(self.id, other_id):
            return False
        
        # Check for pending request (incoming)
        if is_open_invite(other_id, self.id):
            # accept
            accept_friendship(other_id, self.id)
            return True

        # Send invite
        new_friendship(self.id, other_id)
        return True

    @staticmethod
    def attempt_authentication(username, password):
        user = __class__.get_by_username(username)
        if not user:
            return None
        if test_password(password, user.password):
            return user

    @staticmethod
    def get(user_id):
        user = sql("SELECT * FROM Users WHERE uid = ?", [user_id])
        if user:
            return User(user[0][0], user[0][1], user[0][2])
        return None
    
    @staticmethod
    def get_by_username(username):
        user = sql("SELECT * FROM Users WHERE username = ?", [username])
        if user:
            return User(user[0][0], user[0][1], user[0][2])
        return None
    
    @staticmethod
    def create(username, password):
        uid = create_new_user(username, password)
        return User(uid, username, password)