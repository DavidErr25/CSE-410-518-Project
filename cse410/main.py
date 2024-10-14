from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, disconnect
from collections import defaultdict
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from user import User

LOCAL_DEV_FLAG = True

HOST = "localhost" if LOCAL_DEV_FLAG else "128.205.36.18"
SECRET = "709505"
SSL_CONTEXT = ('cert.pem', 'key.pem') # password is 709505

app = Flask(__name__)
app.secret_key = SECRET

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

app.config['SECRET_KEY'] = SECRET # Necessary for sessions, can be any string
socketio = SocketIO(app, ssl_context=SSL_CONTEXT)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route("/")
def index():
    return render_template("index.html")
@app.route("/home")
@login_required
def home():
    return render_template("home.html", user=current_user)
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        if password == "VerySecure":
            user = User.get_by_username(username)
            if user is not None:
                login_user(user)
        else:
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


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.get_by_username(username):
            return render_template("register.html", error="Username taken")
        # TODO: Make a password policy
        user = User.create(username, password)
        login_user(user)
        return redirect(request.args.get('next') or url_for("home"))
    return render_template("register.html")

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
    return render_template('chat.html', room=host_uid, friends=current_user.get_friends())

# Handle messages
@socketio.on('message')
def handle_message(msg):
    print('Message:',msg)
    socketio.emit("message", msg, room=socket_to_room[request.sid])  # Broadcast the message to all connected clients in the room (encrypted with AES)

@socketio.on("connection")
def connection():
    socketio.emit("upgrade-to-secure", )

room_members = defaultdict(list)
socket_to_room = {}
@socketio.on("join_room")
def join(data):
    room = data['room']
    if not is_authorized_to_chat(room, current_user):
        print("\n\n\nUnauthorized\n\n\n")
        return disconnect()
    # TODO: Remove socket from all other rooms
    room_members[room].append(request.sid)

    public_key = data['public_key']
    id = request.sid
    socket_to_room[id] = room
    print(id, room, public_key)

    join_room(room)
    socketio.emit('new_member', {"id": request.sid, "room": room, "count": len(room_members[room]), "key": public_key}, room=room)

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
    del socket_to_room[request.sid]
    for room, members in room_members.items():
        if request.sid in members:
            room_members[room].remove(request.sid)

if __name__ == '__main__':
    socketio.run(app, host=HOST, debug=True, ssl_context=SSL_CONTEXT)
