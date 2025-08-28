"""
FastAPI Full Demo
-----------------
Covers:
- All HTTP methods: GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD
- Query params, request body (JSON/form), file uploads (multipart)
- Pydantic request & response models with validation
- Async/await usage and asyncio background tasks
- Error handling with HTTPException and custom global handlers
- Pagination, filtering, and response_model include/exclude
Run:
    uvicorn app:app --reload
Open docs:
    http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import asyncio
import os
import uvicorn
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    Path,
    status,
    BackgroundTasks,
    Request,
)
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, EmailStr, Field, constr

app = FastAPI(title="FastAPI Full Demo", version="1.0.0")

# ---------------------------------------------------------------------------
# Pydantic Schemas (Requests & Responses)
# ---------------------------------------------------------------------------

class Address(BaseModel):
    city: constr(min_length=2, max_length=50)
    country: constr(min_length=2, max_length=50)

class UserCreate(BaseModel):
    name: constr(min_length=3, max_length=50)
    email: EmailStr
    age: int = Field(..., ge=13, le=120)
    bio: Optional[constr(max_length=200)] = None
    addresses: List[Address] = []

class UserUpdate(BaseModel):
    # Partial update (all optional)
    name: Optional[constr(min_length=3, max_length=50)] = None
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, ge=13, le=120)
    bio: Optional[constr(max_length=200)] = None
    addresses: Optional[List[Address]] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    age: int
    bio: Optional[str] = None
    addresses: List[Address] = []
    created_at: datetime

class PaginatedUsers(BaseModel):
    total: int
    page: int
    limit: int
    items: List[UserResponse]

class UploadResponse(BaseModel):
    filename: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    message: str

# ---------------------------------------------------------------------------
# In-memory "DB"
# ---------------------------------------------------------------------------

USERS: List[Dict] = []
USER_ID = 1

# Helpers

def _find_user_index(user_id: int) -> int:
    for i, u in enumerate(USERS):
        if u["id"] == user_id:
            return i
    return -1

# ---------------------------------------------------------------------------
# Global Error Handling
# ---------------------------------------------------------------------------

class DuplicateEmailError(Exception):
    def __init__(self, email: str):
        self.email = email

@app.exception_handler(DuplicateEmailError)
async def duplicate_email_handler(_: Request, exc: DuplicateEmailError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": True, "message": f"Email already exists: {exc.email}"},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    # Consistent shape for HTTPException responses
    return JSONResponse(status_code=exc.status_code, content={"error": True, "detail": exc.detail})

# ---------------------------------------------------------------------------
# Basic Healthcheck & HEAD/OPTIONS examples
# ---------------------------------------------------------------------------

@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "ok"

@app.head("/health")
async def health_head():
    # HEAD should return headers only; FastAPI manages body omission
    print("HEAD /health called")
    return PlainTextResponse(content="Hello", status_code=200)


@app.options("/users")
async def options_users():
    # Example OPTIONS response
    return JSONResponse(headers={"Allow": "GET,POST,PUT,PATCH,DELETE,OPTIONS"}, content={"ok": True})

# ---------------------------------------------------------------------------
# CREATE (POST) with JSON body validation, duplicate check, async background
# ---------------------------------------------------------------------------

async def send_welcome_email(email: str):
    # Simulate I/O work (email service call)
    await asyncio.sleep(3)
    # In real life: call email provider

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, background: BackgroundTasks):
    global USER_ID

    # Duplicate email check
    if any(u["email"].lower() == user.email.lower() for u in USERS):
        raise DuplicateEmailError(user.email)

    new_user = {
        "id": USER_ID,
        **user.dict(),
        "created_at": datetime.utcnow(),
    }
    USERS.append(new_user)
    USER_ID += 1

    # Fire-and-forget background task
    background.add_task(send_welcome_email, user.email)

    return new_user

# ---------------------------------------------------------------------------
# READ (GET) with query params: pagination, search, filters, include/exclude
# ---------------------------------------------------------------------------

@app.get("/users", response_model=PaginatedUsers)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    q: Optional[str] = Query(None, min_length=2),
    min_age: Optional[int] = Query(None, ge=0),
    max_age: Optional[int] = Query(None, ge=0),
    sort_by: Optional[str] = Query("id", pattern="^(id|name|age)$"),
    order: Optional[str] = Query("asc", pattern="^(asc|desc)$"),
):
    items = USERS.copy()

    # Filtering
    if q:
        q_lower = q.lower()
        items = [u for u in items if q_lower in u["name"].lower() or q_lower in u["email"].lower()]
    if min_age is not None:
        items = [u for u in items if u["age"] >= min_age]
    if max_age is not None:
        items = [u for u in items if u["age"] <= max_age]

    # Sorting
    reverse = order == "desc"
    items.sort(key=lambda u: u[sort_by], reverse=reverse)

    # Pagination
    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    page_items = items[start:end]

    return {"total": total, "page": page, "limit": limit, "items": page_items}

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int = Path(..., ge=1),
    include_addresses: bool = Query(True),
):
    idx = _find_user_index(user_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    user = USERS[idx].copy()
    if not include_addresses:
        user["addresses"] = []
    return user

# ---------------------------------------------------------------------------
# UPDATE (PUT full) & PATCH (partial)
# ---------------------------------------------------------------------------

@app.put("/users/{user_id}", response_model=UserResponse)
async def replace_user(user_id: int, payload: UserCreate):
    idx = _find_user_index(user_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # Duplicate email (exclude current user)
    if any(u["email"].lower() == payload.email.lower() and u["id"] != user_id for u in USERS):
        raise DuplicateEmailError(payload.email)

    USERS[idx].update({**payload.dict()})
    return USERS[idx]

@app.patch("/users/{user_id}", response_model=UserResponse)
async def patch_user(user_id: int, changes: UserUpdate):
    idx = _find_user_index(user_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    update_data = {k: v for k, v in changes.dict(exclude_unset=True).items()}

    # Duplicate email check if email provided
    if "email" in update_data:
        email = update_data["email"]
        if any(u["email"].lower() == email.lower() and u["id"] != user_id for u in USERS):
            raise DuplicateEmailError(email)

    USERS[idx].update(update_data)
    return USERS[idx]

# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@app.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: int):
    idx = _find_user_index(user_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    USERS.pop(idx)
    return {"message": f"User {user_id} deleted"}

# ---------------------------------------------------------------------------
# File Uploads (multipart/form-data) + form fields + query params
# ---------------------------------------------------------------------------

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./_uploads")

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    user_id: Optional[int] = Query(None, ge=1),
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest_path = os.path.join(UPLOAD_DIR, file.filename)

    size = 0
    # Save file asynchronously (chunked)
    with open(dest_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)

    msg = f"Uploaded for user {user_id}" if user_id else "Uploaded"
    if description:
        msg += f" ({description})"

    return UploadResponse(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=size,
        message=msg,
    )

# ---------------------------------------------------------------------------
# Demo endpoint using asyncio.gather to do parallel I/O work
# ---------------------------------------------------------------------------

async def fake_io(delay: float, label: str) -> Dict[str, float | str]:
    await asyncio.sleep(delay)
    return {"task": label, "took": delay}

@app.get("/concurrent-demo")
async def concurrent_demo():
    results = await asyncio.gather(
        fake_io(0.2, "A"),
        fake_io(0.3, "B"),
        fake_io(0.1, "C"),
    )
    return {"results": results}

# ---------------------------------------------------------------------------
# Error examples
# ---------------------------------------------------------------------------

@app.get("/error/bad-request")
async def bad_request_example():
    raise HTTPException(status_code=400, detail="This is a sample bad request error")

@app.get("/error/not-found")
async def not_found_example():
    raise HTTPException(status_code=404, detail="Resource not found")

# ---------------------------------------------------------------------------
# Root welcome
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "message": "Welcome to FastAPI Full Demo",
        "docs": "/docs",
        "endpoints": [
            "/users [GET, POST, OPTIONS]",
            "/users/{user_id} [GET, PUT, PATCH, DELETE]",
            "/upload [POST]",
            "/concurrent-demo [GET]",
            "/health [GET, HEAD]",
        ],
    }

if __name__ == "__main__":
   uvicorn.run("app:app", host="localhost", port=8000, reload=True)