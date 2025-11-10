"""
Database Schemas for the SaaS app

Each Pydantic model maps to a MongoDB collection using the lowercase of the class name.
Examples:
- User -> "user"
- BlogPost -> "blogpost"
- ContactMessage -> "contactmessage"
- PasswordResetToken -> "passwordresettoken"
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class User(BaseModel):
    email: EmailStr = Field(..., description="Unique email address")
    name: Optional[str] = Field(None, description="Full name")
    hashed_password: str = Field(..., description="Password hash")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BlogPost(BaseModel):
    title: str
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: str
    image_url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    message: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PasswordResetToken(BaseModel):
    user_email: EmailStr
    token: str
    expires_at: datetime
    used: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# A helper endpoint in backend will expose these via /schema if needed.
