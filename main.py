from flask import Flask, render_template,  request
from flask_socketio import SocketIO, join_room, leave_room
from collections import defaultdict

LOCAL_DEV_FLAG = True

HOST = "localhost" if LOCAL_DEV_FLAG else "128.205.36.18"
SSL_CONTEXT=('cert.pem', 'key.pem')
# password is 709505

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # Necessary for sessions, can be any string
socketio = SocketIO(app, ssl_context=SSL_CONTEXT)

# from Crypto.PublicKey import RSA
# key = RSA.generate(2048)
# private_key = key.export_key()
# print("Private Key:")
# print(private_key.decode())
# public_key = key.publickey().export_key()
# print("\nPublic Key:")
# print(public_key.decode())

# Serve the chat page
@app.route('/')
def index():
    return render_template('chat.html')

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
