from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_session



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database (replace with a real database in production)
vocabulary = []


class Word(BaseModel):
    word: str


class DeleteWordRequest(BaseModel):
    word: str


@app.post("/api/vocabulary")
def save_word(word: Word):
    if word.word not in vocabulary:
        vocabulary.append(word.word)
        return {"success": True, "message": f"'{word.word}' has been saved!"}
    return {"success": False, "message": f"'{word.word}' already exists."}

@app.get("/api/vocabulary")
def get_vocabulary():
    return vocabulary

@app.delete("/api/vocabulary")
async def delete_word(word_data: DeleteWordRequest):
    """
    Remove a word from the vocabulary list.
    """
    global vocabulary
    word = word_data.word
    if word in vocabulary:
        vocabulary.remove(word)
        return {"success": True, "message": f"'{word}' has been removed!"}
    else:
        raise HTTPException(status_code=404, detail=f"'{word}' not found in vocabulary.")

