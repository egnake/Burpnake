from fastapi import FastAPI, Request, Response, Header
from fastapi.responses import HTMLResponse, JSONResponse
import time
import uvicorn
import sqlite3

app = FastAPI()

# Setup in-memory DB for SQLi testing
conn = sqlite3.connect(':memory:', check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
c.execute("INSERT INTO users (username, password) VALUES ('admin', 'supersecret')")
conn.commit()

@app.get("/")
def read_root():
    return HTMLResponse("<h1>Vulnerable Test Target</h1><ul><li>/sqli?id=1</li><li>/xss?q=test</li><li>/ssrf?url=http://example.com</li><li>/idor/1</li><li>/blind?id=1</li></ul>")

@app.get("/sqli")
def sqli_vuln(id: str = "1"):
    try:
        # Vulnerable to SQLi
        query = f"SELECT * FROM users WHERE id = {id}"
        c.execute(query)
        res = c.fetchone()
        if res:
            return {"user": res[1]}
        return {"error": "Not found"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "trace": "sqlite3.OperationalError"})

@app.get("/xss")
def xss_vuln(q: str = ""):
    # Vulnerable to Reflected XSS
    return HTMLResponse(f"<html><body>Search results for: {q}</body></html>")

@app.get("/ssrf")
def ssrf_vuln(url: str = ""):
    if "169.254" in url or "localhost" in url:
        return {"status": "fetched", "data": "cloud_metadata_mock_or_internal_service"}
    return {"status": "error", "msg": "Could not fetch"}

@app.get("/blind")
def blind_sqli(id: str = "1"):
    # Time-based blind mock
    if "sleep" in id.lower() or "waitfor" in id.lower():
        time.sleep(3)
    
    # Boolean-based mock
    if "or 1=1" in id.lower().replace("'", "").replace('"', ''):
        return {"status": "success", "data": "Admin panel details..."}
    
    return {"status": "success", "data": "Normal user info"}

@app.post("/api/update")
async def mass_assignment(request: Request):
    data = await request.json()
    if data.get("is_admin") == True:
        return {"status": "success", "role": "admin"}
    return {"status": "success", "role": "user"}

if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=9999)