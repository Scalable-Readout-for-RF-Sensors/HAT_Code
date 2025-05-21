# ui.py - Backend server for NanoVNA web interface
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from rf_mux import RFMultiplexer
import uvicorn
from contextlib import asynccontextmanager
import os

mux = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mux
    mux = RFMultiplexer()
    yield
    mux.close()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path) as f:
            return f.read()
    return HTMLResponse("<h1>RF Mux Web Interface</h1><p>No index.html found.</p>", status_code=200)

@app.get("/read/{port}")
def read_port(port: int):
    if mux and 0 <= port < mux.size:
        bit = mux.read(port)
        return {"port": port, "bit": bit}
    return JSONResponse(status_code=400, content={"error": "Invalid port number."})

@app.get("/read_all")
def read_all():
    if mux:
        return mux.readAll()
    return JSONResponse(status_code=500, content={"error": "Multiplexer not initialized."})

@app.get("/switch/{port}")
def switch_port(port: int):
    if mux and 0 <= port < mux.size:
        mux.switchPort(port)
        return {"port": port, "status": "switched"}
    return JSONResponse(status_code=400, content={"error": "Invalid port number."})

if __name__ == "__main__":
    uvicorn.run("ui:app", host="0.0.0.0", port=8000)