from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, disconnect
from collections import defaultdict
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import os
import secrets
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

#store room tokens 
room_tokens = {}

#create tokens
def generate_secure_token():
    return secrets.token_urlsafe(16) 
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
import re
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
@app.route('/chat/<string:token>')
@login_required
def chat(token):
    # Validate the token
    if token not in room_tokens or not is_authorized_to_chat(room_tokens[token], current_user):
        return redirect("/home")
    
    # Get the host UID from the token
    host_uid = room_tokens[token]
    return render_template('chat.html', room=token, friends=current_user.get_friends())

@app.route('/start_chat', methods=['POST'])
@login_required
def start_chat():
    # Assuming the request contains the friend's username
    friend_username = request.form['username']
    friend = User.get_by_username(friend_username)
    
    if not friend or not is_authorized_to_chat(current_user.id, friend):
        return redirect("/home")
    
    # Generate a token and store the mapping
    token = generate_secure_token()
    room_tokens[token] = current_user.id
    
    return redirect(url_for('chat', token=token))


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

@socketio.on("connection")
def connection():
    with activity_lock:
        last_activity[request.sid] = time.time()
    socketio.emit("upgrade-to-secure", )

room_members = defaultdict(list)
socket_to_room = {}
@socketio.on("join_room")
def join(data):
    token = data['room']
    if token not in room_tokens or not is_authorized_to_chat(room_tokens[token], current_user):
        return disconnect()
    
    # Use the token for room management
    room_members[token].append(request.sid)
    socket_to_room[request.sid] = token
    
    join_room(token)
    socketio.emit('new_member', {"id": request.sid, "room": token}, room=token)


@socketio.on("leave_room")
def leave(data):
    room = data['room']
    leave_room(room)
    del socket_to_room[request.sid]
    # Decrement room membership count
    room_members[room].remove(request.sid)


@socketio.on("for")
def msg_for(data):
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
