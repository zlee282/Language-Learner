from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_session as get_db, Vocabulary, User

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Word(BaseModel):
    word: str
    user_id: int = 1  # Default user ID, you might want to implement proper authentication

class DeleteWordRequest(BaseModel):
    word: str
    user_id: int = 1  # Default user ID

@app.post("/api/vocabulary")
def save_word(word: Word, db: Session = Depends(get_db)):
    # Check if word already exists for this user
    existing = db.query(Vocabulary).filter_by(user_id=word.user_id, word=word.word).first()
    if existing:
        return {"success": False, "message": f"'{word.word}' already exists."}
    
    # Add to database
    new_word = Vocabulary(word=word.word, user_id=word.user_id, starred=False)
    db.add(new_word)
    db.commit()
    return {"success": True, "message": f"'{word.word}' has been saved!"}

@app.get("/api/vocabulary")
def get_vocabulary(user_id: int = 1, db: Session = Depends(get_db)):  # Default user ID 1
    words = db.query(Vocabulary).filter_by(user_id=user_id).all()
    return [word.word for word in words]

@app.delete("/api/vocabulary")
async def delete_word(word_data: DeleteWordRequest, db: Session = Depends(get_db)):
    word = db.query(Vocabulary).filter_by(
        user_id=word_data.user_id, 
        word=word_data.word
    ).first()
    
    if word:
        db.delete(word)
        db.commit()
        return {"success": True, "message": f"'{word_data.word}' has been removed!"}
    return {"success": False, "message": f"Word '{word_data.word}' not found."}
