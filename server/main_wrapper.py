"""
Wrapper: 嘗試載入完整 app，失敗時回報錯誤原因
"""
import os
import traceback
from fastapi import FastAPI

# 先啟動一個保底 app
app = FastAPI()
_error_msg = None

@app.get("/health")
def health():
    return {"status": "healthy" if _error_msg is None else "degraded", "error": _error_msg}

@app.get("/_debug")
def debug():
    return {
        "error": _error_msg,
        "PORT": os.environ.get("PORT"),
        "POSTGRES_URI": "set" if os.environ.get("POSTGRES_URI") else "missing",
        "REDIS_URI": "set" if os.environ.get("REDIS_URI") else "missing",
        "DATABASE_URL": os.environ.get("DATABASE_URL", "missing")[:30],
    }

# 嘗試載入完整 app
try:
    from server.main import app as real_app
    app = real_app
except Exception as e:
    _error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-500:]}"
