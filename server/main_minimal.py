import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "port": os.environ.get("PORT", "unset")}

@app.get("/health")
def health():
    return {"status": "healthy"}
