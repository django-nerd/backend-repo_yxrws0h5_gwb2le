import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict

from database import create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# -----------------------------------------------------------------------------
# Schemas endpoint (for Flames DB viewer and tooling)
# -----------------------------------------------------------------------------
from schemas import Character as CharacterSchema, Item as ItemSchema

@app.get("/schema")
def get_schema():
    return {
        "character": CharacterSchema.model_json_schema(),
        "item": ItemSchema.model_json_schema(),
    }

# -----------------------------------------------------------------------------
# API models & routes for Art Library (Characters & Items)
# -----------------------------------------------------------------------------

RARITIES = {"Common", "Rare", "Epic", "Legendary", "Champion"}

class CharacterCreate(BaseModel):
    name: str = Field(...)
    rarity: str = Field(..., description="One of Common, Rare, Epic, Legendary, Champion")
    nation_code: Optional[str] = Field(None, description="ISO like CAN, USA")
    role: Optional[str] = None
    bio: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    palette: Optional[Dict[str, str]] = None
    stats: Optional[Dict[str, int]] = None
    tags: List[str] = []

    def validate_rarity(self):
        if self.rarity not in RARITIES:
            raise HTTPException(status_code=400, detail="Invalid rarity")

class ItemCreate(BaseModel):
    name: str
    type: str
    rarity: str
    effect: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    tags: List[str] = []

    def validate_rarity(self):
        if self.rarity not in RARITIES:
            raise HTTPException(status_code=400, detail="Invalid rarity")

@app.get("/api/characters")
def list_characters(limit: int = 100):
    docs = get_documents("character", limit=limit)
    # Convert ObjectId to string
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return {"items": docs}

@app.post("/api/characters")
def create_character(payload: CharacterCreate):
    payload.validate_rarity()
    _id = create_document("character", payload.model_dump())
    return {"id": _id}

@app.get("/api/items")
def list_items(limit: int = 100):
    docs = get_documents("item", limit=limit)
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return {"items": docs}

@app.post("/api/items")
def create_item(payload: ItemCreate):
    payload.validate_rarity()
    _id = create_document("item", payload.model_dump())
    return {"id": _id}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
