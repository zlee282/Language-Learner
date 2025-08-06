# sqlalchemy: library to interact with databases in python
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import requests

Base = declarative_base() #This variable is the base for defining all database models

# Database setup
def get_engine(): # a function that creates a connection to a database
    return create_engine("sqlite:///users.db") 

def get_session(): #creates a session object. Sessions handle queries and updates
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

# User model
class User(Base): #defines a database table 
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True) #a column storing unique numbers for each user
    username = Column(String, unique=True, nullable=False) #a column storing the usernames of each user
    password = Column(String, nullable=False) #a column storing the passwords of each user
    nativeLang = Column(String, nullable = True)
    newLang = Column(String, nullable = True)
    proficiency = Column(String, nullable = True)
    vocabulary = relationship("Vocabulary", back_populates="user")

class Vocabulary(Base):
    __tablename__ = 'vocabulary'
    id = Column(Integer, primary_key=True)
    word = Column(String, nullable=False)
    starred = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="vocabulary")
    timestamp = Column(DateTime, default=datetime.utcnow)

# Initialize database
def init_db(): #a function that creates the database table defined above
    engine = get_engine()
    Base.metadata.create_all(engine)

def dataset_db():
    session = get_session()
    users = session.query(User.username, User.password).all()
    engine = get_engine()
    Base.metadata.drop_all(engine)  # Drop all tables
    Base.metadata.create_all(engine)  # Recreate tables with updated schema
    session = get_session()
    for username, password in users:
        user = User(username=username, password=password, nativeLang="English", newLang="Spanish", proficiency="Beginner")
        session.add(user)
    session.commit()

def get_all_usernames():
    session = get_session()
    usernames = session.query(User.username).all()
    return [username[0] for username in usernames]

def get_all_passwords():
    session = get_session()
    passwords = session.query(User.password).all()
    return [password[0] for password in passwords]


def get_user_vocabulary(user_id, show_starred_only=False):
    session = get_session()
    query = session.query(Vocabulary).filter_by(user_id=user_id)
    if show_starred_only:
        query = query.filter_by(starred=True)
    return query.order_by(Vocabulary.timestamp.desc()).all()

def toggle_star_word(word_id, user_id):
    session = get_session()
    word = session.query(Vocabulary).filter_by(id=word_id, user_id=user_id).first()
    if word:
        word.starred = not word.starred
        session.commit()
        return True
    return False

def remove_vocabulary_word(word_id: int, user_id: int) -> bool:
    """
    Remove a word from the user's vocabulary and sync with the browser extension.
    """
    session = get_session()
    word = session.query(Vocabulary).filter_by(id=word_id, user_id=user_id).first()
    
    if word:
        word_text = word.word  # Save the word text before deleting
        session.delete(word)
        session.commit()
        
        # Try to sync with browser extension
        try:
            response = requests.delete(
                "http://localhost:8000/api/vocabulary",
                json={"word": word_text}
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # Silently fail if the extension is not running
            pass
            
        return True
    return False

def get_starred_words(user_id):
    session = get_session()
    return [word.word for word in session.query(Vocabulary).filter_by(user_id=user_id, starred=True).all()]
