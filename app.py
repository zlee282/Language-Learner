from openai import OpenAI
import random
import streamlit as st
import os
import base64
from dotenv import load_dotenv
from auth import register_user, authenticate_user
from database import get_session, User, Vocabulary, get_user_vocabulary, toggle_star_word, remove_vocabulary_word, get_starred_words
from database import init_db
import requests
import time
from typing import List, Optional
from streamlit_extras.let_it_rain import rain

# Load environment variables
load_dotenv()

# Set page config first
st.set_page_config(
    page_title="Language Helper",
    page_icon="📚",
    layout="wide"
)

def load_css(file):
    with open(file) as f:
        st.html(f"<style>{f.read()}</style>")
css_path = "style.css"
load_css(css_path)

def get_img_as_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

img=get_img_as_base64("App_Background.jpg")
sidebar_img = get_img_as_base64("sidebar.jpg")

page_bg_img = f"""
<style>
[data-testid="stAppViewContainer"]{{
    background-image: url("data:image/jpeg;base64,{img}");
    background-size: cover;
    position: relative;

}}

[data-testid="stToolbar"]{{
    background-color: rgba(255, 255, 255, 0.8);
}}

[data-testid="stSidebar"]{{
    background-image: url("data:image/jpeg;base64,{sidebar_img}");
    background-size: cover;
    position: center;
}}
</style>
"""

st.markdown(page_bg_img, unsafe_allow_html=True)

st.logo(
    "language_helper_logo.png",
    icon_image="language_helper_logo.png",
)

# Initialize the database
init_db()  # creates database

# Get API key from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)
 
def emojiRain():
    rain(
        emoji="🎊",
        font_size=54,
        falling_speed=3,
        animation_length=1,
    )

def add_vocabulary_word(user_id, word):
    """Add a word to the user's vocabulary and sync with FastAPI server"""
    session = get_session()
    # Check if word already exists for this user
    existing = session.query(Vocabulary).filter_by(user_id=user_id, word=word).first()
    if existing:
        return False  # Word already exists
    
    # Add to database
    new_word = Vocabulary(word=word, starred=False, user_id=user_id)
    session.add(new_word)
    session.commit()
    
    # Sync with FastAPI server
    sync_success = sync_vocabulary_with_server(user_id, 'add', word)
    if not sync_success:
        print(f"Warning: Failed to sync word '{word}' with FastAPI server")
    
    return True

def import_vocabulary_from_extension(user_id: int) -> None:

    #Fetch words from the browser extension and add them to the user's vocabulary. Only adds words that don't already exist for the user.
    try:
        response = requests.get("http://localhost:8000/api/vocabulary")
        response.raise_for_status()
        words = response.json()
        
        if not isinstance(words, list):
            st.error("Unexpected response format from vocabulary API")
            return
            
        session = get_session()
        imported_count = 0
        
        for word in words:
            if not isinstance(word, str):
                continue
                
            # Check if word already exists for user
            existing = session.query(Vocabulary).filter_by(user_id=user_id, word=word).first()
            if not existing:
                vocab = Vocabulary(word=word, starred=False, user_id=user_id)
                session.add(vocab)
                imported_count += 1
        
        if imported_count > 0:
            session.commit()
            st.sidebar.success(f"Imported {imported_count} new words from browser extension!")
            
    except requests.exceptions.RequestException as e:
        # Silently fail. extension might not be running
        pass

def sync_vocabulary_with_server(user_id: int, action: str, word: str = None):
    """
    Sync vocabulary changes with the FastAPI server
    
    Args:
        user_id: The ID of the current user
        action: One of 'add', 'delete', 'update_star'
        word: The word being modified (required for 'add' and 'delete' actions)
    """
    try:
        print(f"Attempting to sync: action={action}, word={word}")  # Debug log
        if action in ['add', 'delete'] and not word:
            print("Error: Word is required for add/delete actions")  # Debug log
            return False
            
        session = get_session()
        
        if action == 'add':
            # Check if word exists in database
            existing = session.query(Vocabulary).filter_by(user_id=user_id, word=word).first()
            if not existing:
                print(f"Adding word to FastAPI server: {word}")  # Debug log
                response = requests.post(
                    "http://localhost:8000/api/vocabulary",
                    json={"word": word, "user_id": user_id},
                    timeout=5
                )
                print(f"Server response: {response.status_code}, {response.text}")  # Debug log
                return response.status_code == 200
            else:
                print(f"Word '{word}' already exists in the database")  # Debug log
                return False
                
        elif action == 'delete':
            print(f"Deleting word from FastAPI server: {word}")  # Debug log
            response = requests.delete(
                "http://localhost:8000/api/vocabulary",
                json={"word": word, "user_id": user_id},
                timeout=5
            )
            print(f"Server response: {response.status_code}, {response.text}")  # Debug log
            return response.status_code == 200
            
        elif action == 'update_star':
            # For star updates, we don't need to sync with the FastAPI server
            # since the extension only needs the word list
            print("Star update - no sync needed with FastAPI")  # Debug log
            return True
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to sync with vocabulary server: {str(e)}"
        print(error_msg)  # Debug log
        st.error(error_msg)
        return False

with st.container(key="title_container"):
    st.title("Where Voices Meet")

menu = st.sidebar.selectbox("", ["Login", "Register", "My Settings", "Quiz me", "Revise my writing", "My Vocabulary List"]) #adds a dropdown menu on the sidebar 
 
# Session management
if "logged_in" not in st.session_state: 
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.q_generated = False
    st.session_state.currentQuestion = None
    st.session_state.currentWord = None
    st.session_state.show_registration_success = False

if menu == "Register":
    with st.container(key="login_register_container"):
        st.markdown("<div class='form-container'>", unsafe_allow_html=True)
        st.subheader("Create a New Account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        st.markdown("</div>", unsafe_allow_html=True)
        register_button = st.button("Register", key="buttons")
    
    if st.session_state.show_registration_success:
        st.success("Registration successful! You are now logged in.")
        st.session_state.show_registration_success = False  # Reset the flag
    
    
    
    if register_button:
        if not username.strip():
            st.error("Username cannot be empty.")
        elif not password.strip():
            st.error("Password cannot be empty.")
        elif register_user(username, password):
            # Set login state and username
            st.session_state.logged_in = True
            st.session_state.username = username
            
            # Get user ID to import vocabulary
            session = get_session()
            user = session.query(User).filter_by(username=username).first()
            
            # Import words from browser extension
            import_vocabulary_from_extension(user.id)
            
            emojiRain()
            st.session_state.show_registration_success = True
            st.rerun()  # This will cause the success message to show on the next run
        else:
            st.error("Username already exists. Please try a different one.")

elif menu == "Login":
    with st.container(key="login_register_container"):
        st.markdown("<div class='form-container'>", unsafe_allow_html=True)
        st.subheader("Log in to Your Account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        st.markdown("</div>", unsafe_allow_html=True)
        login_button = st.button("Login", key="buttons")
        
        
        if login_button:
            if authenticate_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                session = get_session()
                user = session.query(User).filter_by(username=username).first()
            
                # Import words from browser extension
                import_vocabulary_from_extension(user.id)
            
                st.success(f"Welcome back, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password. Please try again.")

if st.session_state.logged_in:
    st.sidebar.markdown(f'<p style="color: #8fa6bb; font-size: 20px; font-family: times new roman">Logged in as {st.session_state.username}</p>', unsafe_allow_html=True)
    if st.sidebar.button("Log out"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.success("You have logged out.")
        



def update_user_info(username, new_username=None, new_password=None, new_newLang=None):
    session = get_session()
    user = session.query(User).filter_by(username=username).first()  # Find the user
    if user:
        if new_username:
            user.username = new_username  # Update username
        if new_password:
            user.password = new_password  # need to hash password before storing
        if new_newLang:
            user.newLang = new_newLang
        session.commit()  # Save changes
        return True
    return False  # User not found

def get_newLang(username):
    session = get_session()
    user = session.query(User).filter_by(username=username).first()  # Find the user
    if user:
        return user.newLang
    return "No user found"


if menu=="My Settings":
    if st.session_state.logged_in:
        with st.container(key="login_register_container"):
            st.markdown("<div class='form-container'>", unsafe_allow_html=True)
            st.subheader("Change your settings!")
            st.subheader("Current Language: " + str(get_newLang(st.session_state.username))) 
            newLang = st.selectbox("New Language", ["Spanish","Chinese"])
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button("Save"):
                update_user_info(st.session_state.username, new_newLang=newLang)
                st.rerun()

    else:
        st.error("You are not logged in.")


if menu=="My Vocabulary List":
    if st.session_state.logged_in:
        with st.container(key="login_register_container"):
            st.subheader("My Vocabulary List")
        
            # Get current user
            session = get_session()
            user = session.query(User).filter_by(username=st.session_state.username).first()
        
            # Sync with browser extension
            if user:
                import_vocabulary_from_extension(user.id)
        
            # Add new word
            with st.expander("Add a new word", expanded=False):
                new_word = st.text_input("Enter a new word to add to your vocabulary:")
                if st.button("Add Word") and new_word:
                    if add_vocabulary_word(user.id, new_word):
                        st.success(f"Added '{new_word}' to your vocabulary!")
                        sync_vocabulary_with_server(user.id, 'add', new_word)
                        st.rerun() 
                    else:
                        st.warning(f"'{new_word}' is already in your vocabulary!")
        
            # Filter options
            show_starred_only = st.checkbox("Show starred words only")
        
            # Display vocabulary list
            vocab_list = get_user_vocabulary(user.id, show_starred_only=show_starred_only)
        
            if not vocab_list:
                st.info("No words found. Add some words to get started!")
            else:
                # Display word count
                st.write(f"You have {len(vocab_list)} words in your vocabulary")
            
                # Add a search box
                search_term = st.text_input("Search your vocabulary:", "")
            
                for item in vocab_list:
                    # Skip words that don't match search
                    if search_term.lower() not in item.word.lower():
                        continue
                    
                    col1, col2, col3 = st.columns([6, 1, 1])
                    with col1:
                        st.write(f"{item.word}")
                    with col2:
                        star_emoji = "⭐" if item.starred else "☆"
                        if st.button(star_emoji, key=f"star_{item.id}"):
                            toggle_star_word(item.id, user.id)
                            sync_vocabulary_with_server(user.id, 'update_star')
                            st.rerun()
                    with col3:
                        if st.button("🗑️", key=f"del_{item.id}"):
                            remove_vocabulary_word(item.id, user.id)
                            sync_vocabulary_with_server(user.id, 'delete', item.word)
                            st.rerun()
                    st.write("---")
    else:
        st.error("Please log in to view your vocabulary list.")

if menu=="Quiz me":
    if st.session_state.logged_in:
        with st.container(key="login_register_container"):
            st.subheader("Quiz Me")
            generate_question_button = st.button("Generate Quiz Question", key="buttons")
        
            # Get current user
            session = get_session()
            user = session.query(User).filter_by(username=st.session_state.username).first()
        
            # Get starred words for quiz
            starred_words = get_starred_words(user.id)
        
            if not starred_words:
                st.warning("You don't have any starred words yet. Star some words in your vocabulary list first!")
            else:
                if generate_question_button:
                    random_word = random.choice(starred_words)
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You are a language teacher helping a student learn a new language through quizzing them about new vocabulary words."},
                            {"role": "user", "content": f"You are talking directly to the student. Write a question that will prompt the student to put the word '{random_word}' into context. Please respond in {get_newLang(st.session_state.username)}."}
                        ]
                    )
                    reply = response.choices[0].message.content
                    st.session_state.q_generated = True
                    st.session_state.currentQuestion = reply
                    st.session_state.currentWord = random_word
                   
                
                if st.session_state.q_generated:
                    st.write("---")  # Add a separator
                    st.markdown("<div class='quiz-content'>", unsafe_allow_html=True)
                    st.subheader(st.session_state.currentQuestion)
                    student_response = st.text_area("Your Answer", "Your Answer Here...", key="student_response")
                    if st.button("Submit and get feedback!", key="submit_button"):
                        emojiRain()
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "You are a language teacher helping a student learn a new language by giving them feedback on their writing."},
                                {"role": "user", "content": f"The student is responding to this prompt: {st.session_state.currentQuestion}\nThe student's writing: {student_response}\nThe word they were supposed to use is: {st.session_state.currentWord}\nPlease check if they used the word correctly and naturally in their response. List at least 1 strength and give the student 1-2 pieces of feedback on their writing. Evaluate the student's writing with an emphasis on the student’s contextualization of the vocabulary word. Please respond in English and respond as if you were speaking directly to the student."}
                            ]
                        )
                        reply = response.choices[0].message.content
                        with st.container(key="reply_container"):
                            st.subheader(reply)
                        st.session_state.q_generated = False
                        st.session_state.currentQuestion = None
                        st.session_state.currentWord = None
                    st.markdown("</div>", unsafe_allow_html=True)

if menu=="Revise my writing":
    with st.container(key="login_register_container"):
        st.subheader("Revise my writing")
        if st.session_state.logged_in:
            student_response = st.text_area("Student writing", "your ideas here....", key="student_response")
            if st.button("Submit and get feedback!"):
                emojiRain()
                response = client.chat.completions.create(
                    model="gpt-4o",  # Use "gpt-3.5-turbo" for the cheaper model
                    messages=[
                        {"role": "system", "content": "You are a language teacher helping a student learn a new language by giving them feedback on their writing."},
                        {"role": "user", "content": "This is the student's writing: " + str(student_response) + "\n Please give the student feedback on social convention. For example, give feedback on whether the student's writing aligns with the country's social customs or whether the words and phrases the student is using are culturally appropriate. If the student spoke this way, would they sound like a native speaker? If not, how can they improve? Also give feedback on the student's grammar or in any areas in which there is room for improvement. Please respond as if you are speaking directly to the student and respond in English."}
                    ]
                )
                reply = response.choices[0].message.content
            
                st.subheader(reply)