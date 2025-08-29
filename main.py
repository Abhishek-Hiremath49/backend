from fastapi import FastAPI

app = FastAPI()

@app.get("/",tags=["Root"])
def read_root():
    return 'hey'