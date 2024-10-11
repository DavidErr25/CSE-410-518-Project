from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
SSL_KEY = 'key.pem'
SSL_CERT = 'cert.pem'
SSL_CONTEXT=(SSL_CERT, SSL_KEY)

# Initialize SocketIO with SSL context
socketio = SocketIO(app, ssl_context=SSL_CONTEXT)

@app.route('/')
def index():
    return "Welcome to Flask-SocketIO with SSL!"

if __name__ == '__main__':
    # Run the app on port 5000
    socketio.run(app, host='0.0.0.0', port=5000, ssl_context=SSL_CONTEXT)
