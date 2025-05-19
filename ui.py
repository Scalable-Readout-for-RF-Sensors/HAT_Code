# ui.py - Backend server for NanoVNA web interface

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
from nanovna import NanoVNA
from rf_mux import RFMultiplexer

app = FastAPI()

# CORS setup for Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend files
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

nvna = NanoVNA()
nvna.open()
mux = RFMultiplexer(size=12)

class ReadRequest(BaseModel):
    port: int

@app.get("/read_all")
async def read_all():
    results = mux.readAll()
    return JSONResponse(content=results)

@app.post("/read_port")
async def read_port(req: ReadRequest):
    bit = mux.read(req.port)
    return JSONResponse(content={"port": req.port, "bit": bit})

@app.get("/plot")
async def get_plot():
    mux.switchPort(0)  # Default to port 0
    freqs = nvna.frequencies
    s11 = nvna.data(0)
    s11_db = 20 * np.log10(np.abs(s11))

    fig, ax = plt.subplots()
    ax.plot(freqs / 1e6, s11_db)
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("S11 Magnitude (dB)")
    ax.set_title("S11 Plot")
    ax.grid(True)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return JSONResponse(content={"image": f"data:image/png;base64,{img_base64}"})

if __name__ == "__main__":
    uvicorn.run("ui:app", host="0.0.0.0", port=80, reload=True)
