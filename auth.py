from database import User, get_session
from utils import hash_password, check_password

def register_user(username, password):
    session = get_session() #opens a database session
    if session.query(User).filter_by(username=username).first(): #checking if this username already exists
        return False  # Username already exists
    new_user = User(username=username, password=hash_password(password), nativeLang="English", newLang="Spanish", proficiency="Beginner") #hash password -> encrypt the passwords before storing it
    session.add(new_user) #add new user to database
    session.commit() #save changes to the database
    return True #indicates successful registration

def authenticate_user(username, password):
    session = get_session()
    user = session.query(User).filter_by(username=username).first() #fetches user with matching username
    if user and check_password(password, user.password):
        return True
    return False
