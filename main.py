import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from database import db, create_document, get_documents

app = FastAPI(title="SaaS Starter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====== Pydantic request/response models ======
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str


class BlogPostCreate(BaseModel):
    title: str
    excerpt: Optional[str] = None
    content: str
    image_url: Optional[str] = None
    author: Optional[str] = None


# ====== Utility helpers ======
from hashlib import sha256

def hash_password(pw: str) -> str:
    salt = os.getenv("APP_SALT", "static_salt_change_me")
    return sha256((salt + pw).encode()).hexdigest()


# ====== Routes ======
@app.get("/")
def root():
    return {"message": "SaaS Backend running"}


@app.get("/test")
def test_database():
    response = {"backend": "✅ Running", "database": "❌ Not Available"}
    try:
        if db is not None:
            response["database"] = "✅ Connected"
            response["collections"] = db.list_collection_names()
    except Exception as e:
        response["database"] = f"⚠️ {str(e)[:80]}"
    return response


# ---- Auth (simple, demo) ----
@app.post("/auth/signup")
def signup(payload: SignupRequest):
    users = db["user"]
    if users.find_one({"email": payload.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    doc = {
        "email": payload.email,
        "name": payload.name,
        "hashed_password": hash_password(payload.password),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    users.insert_one(doc)
    return {"ok": True, "message": "Account created. You can now log in."}


@app.post("/auth/login")
def login(payload: LoginRequest):
    users = db["user"]
    user = users.find_one({"email": payload.email})
    if not user or user.get("hashed_password") != hash_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # Demo token (not JWT) for simplicity
    token = sha256(f"{payload.email}:{datetime.utcnow()}".encode()).hexdigest()
    return {"ok": True, "token": token, "user": {"email": user.get("email"), "name": user.get("name")}}


@app.post("/auth/forgot")
def password_reset_request(payload: PasswordResetRequest):
    users = db["user"]
    user = users.find_one({"email": payload.email})
    if not user:
        # do not reveal user existence
        return {"ok": True, "message": "If that email exists, a reset link was sent."}
    token = uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(hours=1)
    db["passwordresettoken"].insert_one({
        "user_email": payload.email,
        "token": token,
        "expires_at": expires_at,
        "used": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    # In a real app, send email. Here we return token for demo/preview.
    return {"ok": True, "message": "Reset email sent.", "preview_token": token}


@app.post("/auth/reset")
def password_reset_confirm(payload: PasswordResetConfirm):
    rec = db["passwordresettoken"].find_one({"token": payload.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid token")
    if rec.get("expires_at") < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")
    db["user"].update_one({"email": rec["user_email"]}, {"$set": {
        "hashed_password": hash_password(payload.new_password),
        "updated_at": datetime.utcnow(),
    }})
    db["passwordresettoken"].update_one({"_id": rec["_id"]}, {"$set": {"used": True, "updated_at": datetime.utcnow()}})
    return {"ok": True, "message": "Password has been reset."}


# ---- Blog ----
@app.get("/blog")
def list_blog_posts():
    posts = db["blogpost"].find().sort("published_at", -1)
    out = []
    for p in posts:
        out.append({
            "id": str(p.get("_id")),
            "title": p.get("title"),
            "excerpt": p.get("excerpt"),
            "image_url": p.get("image_url"),
            "author": p.get("author"),
            "published_at": p.get("published_at"),
            "slug": p.get("slug"),
        })
    return out


@app.get("/blog/{slug}")
def get_blog_post(slug: str):
    post = db["blogpost"].find_one({"slug": slug})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return {
        "id": str(post.get("_id")),
        "title": post.get("title"),
        "content": post.get("content"),
        "image_url": post.get("image_url"),
        "author": post.get("author"),
        "published_at": post.get("published_at"),
        "slug": post.get("slug"),
    }


@app.post("/blog")
def create_blog_post(payload: BlogPostCreate):
    # generate slug
    base_slug = (payload.title.lower().strip().replace(" ", "-").replace("/", "-")[:60])
    slug = base_slug
    i = 1
    while db["blogpost"].find_one({"slug": slug}):
        i += 1
        slug = f"{base_slug}-{i}"
    doc = {
        "title": payload.title,
        "excerpt": payload.excerpt,
        "content": payload.content,
        "image_url": payload.image_url,
        "author": payload.author or "Team",
        "published_at": datetime.utcnow(),
        "slug": slug,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    db["blogpost"].insert_one(doc)
    return {"ok": True, "slug": slug}


# ---- Contact ----
@app.post("/contact")
def submit_contact(payload: ContactRequest):
    create_document("contactmessage", payload.model_dump())
    return {"ok": True, "message": "Thanks for reaching out!"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
