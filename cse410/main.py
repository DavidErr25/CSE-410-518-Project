from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, disconnect
from collections import defaultdict
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import os
import re
import time
from threading import Lock

from dotenv import load_dotenv
load_dotenv()

from user import User
from util import rate_limit

HOST = "0.0.0.0"
SECRET = os.getenv('SECRET')
SSL_CONTEXT = ('cert.pem', 'key.pem')

app = Flask(__name__)
app.secret_key = SECRET

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

app.config['SECRET_KEY'] = SECRET # Necessary for sessions, can be any string
socketio = SocketIO(app, ssl_context=SSL_CONTEXT)

INACTIVITY_TIMEOUT = 10*60

last_activity = {}
activity_lock = Lock()
# Background task to monitor inactivity
def monitor_inactivity():
    while True:
        with app.app_context():
            print("Monitoring inactivity...")
            now = time.time()
            to_disconnect = []
            
            with activity_lock:
                for sid, last_time in last_activity.items():
                    if now - last_time > INACTIVITY_TIMEOUT:
                        to_disconnect.append(sid)

            for sid in to_disconnect:
                socketio.emit("custom-kill", {"message": "Disconnected due to inactivity."}, to=sid)
                print(f"Killed {sid}")
                logout_user()
                with activity_lock:
                    last_activity.pop(sid, None)

            time.sleep(10)  # Check every minute

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)
 

@app.route("/")
def index():
    return render_template("index.html")
@app.route('/timeout')
def timeout():
    logout_user()
    return render_template("timeout.html")
@app.route("/home")
@login_required
def home():
    return render_template("home.html", user=current_user)
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.attempt_authentication(username, password)
        if user is not None:
            login_user(user)
        if user is not None:
            return redirect(request.args.get('next') or url_for("home"))
    return render_template("login.html")
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

'''
Password Policy:

Minimum eight characters, at least one uppercase letter,
one lowercase letter, one number and one special character:
'''
PASSWORD_POLICY = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if not re.search(PASSWORD_POLICY, password):
            return render_template("login.html", error="Your password must conform: Minimum eight characters, at least one uppercase letter, one lowercase letter, one number and one special character")
        if User.get_by_username(username):
            return render_template("login.html", error="Username taken")
        # TODO: Make a password policy
        user = User.create(username, password)
        login_user(user)
        return redirect(request.args.get('next') or url_for("home"))
    return render_template("login.html", error="")

@app.route("/invite", methods=["POST"])
def invite():
    print(f"Current: {current_user.username}")
    current_user.add_friend(request.form["username"])
    return redirect(url_for("home"))

@app.route('/whoami')
@login_required
def whoami():
    return f'Logged in as: {current_user.username}'


def is_authorized_to_chat(host_uid, other):
    print(f"Attempt\nHost: {host_uid}\nOther: {other.id}\n\n")
    if host_uid == other.id:
        return True
    print(other.get_friends())
    if host_uid in other.get_friends():
        return True
    return False

# Serve the chat page
@app.route('/chat/<string:host_uid>')
@login_required
def chat(host_uid):
    # TODO: Allow host to lock rooms
    if not is_authorized_to_chat(host_uid, current_user):
        return redirect("/home")
    if host_uid in locked_rooms:
        print("app checking accesss.")
        print(current_user.id, locked_rooms[host_uid])
        if current_user.id not in locked_rooms[host_uid]:
            return redirect("/home?locked")
    return render_template('chat.html', room=host_uid, you=current_user.id, friends=current_user.get_friends())

# Handle messages
@socketio.on('message')
@rate_limit(10)
def handle_message(msg):
    sender = current_user.username
    sid = request.sid

    # Update the last activity timestamp
    with activity_lock:
        last_activity[sid] = time.time()

    message_data = {
        'message': msg,
        'sender': sender
    }
    print('Message:', message_data)
    socketio.emit("message", message_data, room=socket_to_room[request.sid])  # Broadcast the message to all connected clients in the room (encrypted with AES)

socket_to_uid = {}
@socketio.on("connect")
def connection():
    print("Connection!\n"*10)
    global socket_to_uid
    socket_to_uid[request.sid] = current_user.id
    print(f"Connection: {socket_to_uid}")
    with activity_lock:
        last_activity[request.sid] = time.time()
    socketio.emit("upgrade-to-secure", )

locked_rooms = {}
@socketio.on("lock_room")
def lock_room():
    # print(socket_to_uid)
    current_room = socket_to_room[request.sid]
    if current_user.id == current_room:
        current_users = set(map(lambda sid: socket_to_uid[sid], room_members[current_room]))
        print(f"Locking room {current_room}")
        print(f"Users: {current_users}")
        if current_room not in locked_rooms:
            locked_rooms[current_room] = current_users
@socketio.on("unlock_room")
def lock_room():
    current_room = socket_to_room[request.sid]
    print(f"Unlocking room {current_room}")
    if current_user.id == current_room: # rooms are named after host
        if current_room in locked_rooms:
            del locked_rooms[current_room]

room_members = defaultdict(list)
socket_to_room = {}
@socketio.on("join_room")
def join(data):
    room = data['room']
    if not is_authorized_to_chat(room, current_user):
        print("\n\n\nUnauthorized\n\n\n")
        return disconnect()
    if room in locked_rooms:
        print("Checking access")
        print(locked_rooms[room], current_user.id)
        if current_user.id not in locked_rooms[room]:
            return disconnect()
    # TODO: Remove socket from all other rooms
    room_members[room].append(request.sid)

    public_key = data['public_key']
    id = request.sid
    socket_to_room[id] = room
    print(id, room, public_key)

    join_room(room)
    socketio.emit('new_member', {"id": request.sid, "room": room, "count": len(room_members[room]), "key": public_key, "locked": (room in locked_rooms) }, room=room)

@socketio.on("leave_room")
def leave(data):
    room = data['room']
    leave_room(room)
    del socket_to_room[request.sid]
    # Decrement room membership count
    room_members[room].remove(request.sid)


@socketio.on("for")
def msg_for(data):
    if not (request.sid in room_members and len(room_members[request.sid] > 0)):
        return disconnect()
    sid = data['id']
    key = data['data']
    print("-"*20)
    print(f"{sid}: {key}")
    print("-"*20)
    socketio.emit("room_key", key, to=sid)

@socketio.on("disconnect")
def gone():
    with activity_lock:
        last_activity.pop(request.sid, None)
    del socket_to_room[request.sid]
    for room, members in room_members.items():
        if request.sid in members:
            room_members[room].remove(request.sid)

if __name__ == '__main__':
    socketio.start_background_task(monitor_inactivity)
    socketio.run(app, host=HOST, debug=False, ssl_context=SSL_CONTEXT)
