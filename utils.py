import bcrypt # library for hashing and validating passwords

def hash_password(password): #returns encrypted password
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed): #checks user's plain password against the encrypted password
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
