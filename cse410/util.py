import bcrypt

def hash(password_string):
    bytes = password_string.encode('utf-8')
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(bytes, salt)

    return hash

def test_password(plaintext, hashed):
    return bcrypt.checkpw(plaintext.encode("utf-8"), hashed)

def sql_to_dict(columns, sql_output):
    return [{k:v for k,v in zip(columns, entry)} for entry in sql_output]


from flask_limiter.util import get_remote_address
import time
rate_limits = {}

def rate_limit(limit_per_minute):
    def decorator(func):
        def wrapper(*args, **kwargs):
            ip = get_remote_address()
            now = time.time()
            if ip not in rate_limits:
                rate_limits[ip] = []
            rate_limits[ip] = [t for t in rate_limits[ip] if t > now - 60]  # Keep only timestamps within the last minute
            if len(rate_limits[ip]) < limit_per_minute:
                rate_limits[ip].append(now)
                return func(*args, **kwargs)
            else:
                print("Rate limit exceeded")
        return wrapper
    return decorator
