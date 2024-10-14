import sqlite3
from util import sql_to_dict

conn = sqlite3.connect("friends.sqlite", check_same_thread=False)
def sql(query, params=None):
    if params is None:
        params = ()
    cur = conn.cursor()
    data = cur.execute(query, params).fetchall()
    conn.commit()
    cur.close()
    return data

columns = ["id", "friend1", "friend2", "confirmed"]
sql("CREATE TABLE IF NOT EXISTS Friends (uid INTEGER PRIMARY KEY AUTOINCREMENT, friend1 varchar(255), friend2 varchar(255), confirmed INT)")
# invite iff confirmed = 0

def is_open_invite(uid1, uid2):
    results = sql("SELECT * FROM Friends WHERE friend1=? AND friend2=? AND confirmed=0", (uid1, uid2))
    return len(results) > 0

def accept_friendship(uid1, uid2):
    sql("UPDATE Friends SET confirmed=1 WHERE friend1=? AND friend2=?", (uid1, uid2))

def new_friendship(uid1, uid2, confirmed=0):
    # TODO: Add error handling and input validation
    sql("INSERT INTO Friends (friend1, friend2, confirmed) VALUES (?, ?, ?)", (uid1, uid2, confirmed))

def are_friends(uid1, uid2): # price of disorganization
    return uid2 in friends_of(uid1)

def friends_of(uid):
    print(f"\n\nFriends of {uid}")
    _1 = sql("SELECT friend2 FROM Friends WHERE friend1=? AND confirmed=1", [uid])
    _2 = sql("SELECT friend1 FROM Friends WHERE friend2=? AND confirmed=1", [uid])
    m1 = list(map(lambda x: x[0], _1))
    m1.extend(map(lambda x: x[0], _2))
    return m1

# TODO: Add a way to remove friendships