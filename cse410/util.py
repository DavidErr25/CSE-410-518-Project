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