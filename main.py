from flask import Flask, render_template
from flask_socketio import SocketIO, send

LOCAL_DEV_FLAG = False

HOST = "localhost" if LOCAL_DEV_FLAG else "128.205.36.18"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # Necessary for sessions, can be any string
socketio = SocketIO(app)

# Serve the chat page
@app.route('/')
def index():
    return render_template('chat.html')

# Handle messages
@socketio.on('message')
def handle_message(msg):
    print('Message:',msg)
    send(msg, broadcast=True)  # Broadcast the message to all connected clients

if __name__ == '__main__':
    socketio.run(app, host=HOST, debug=True)
