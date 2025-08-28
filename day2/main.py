from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from typing import Optional

app = FastAPI()

class DataModel(BaseModel):
    name: str
    age: int
    id: int
    Usn: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Hello! Wellcome to FastAPI"}

@app.get("/about")
def read_about():
    return {"message": "About Page"}

@app.post("/submit")
def submit_data(abhi: list[DataModel]):
    return {"message": "Data received", "data": [item.dict() for item in abhi]}

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
