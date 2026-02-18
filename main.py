from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from analysis import run_analysis
import uvicorn

app = FastAPI()

# CORS 설정 (프론트엔드 통신 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/analyze")
async def analyze():
    return run_analysis()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
