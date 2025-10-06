import sys
import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

# --- Add project root to Python path ---
# This is to ensure that all modules can be imported correctly, regardless of how the app is run.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End of path modification ---

from server.api.weather import router as weather_router
from server.scheduler.jobs import scheduler

load_dotenv()

app = FastAPI(
    title="Weather Forecast API",
    description="API for providing weather forecasts and sending notifications.",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    print("FastAPI application startup")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("FastAPI application shutdown")

@app.get("/")
async def root():
    return {"message": "Welcome to the Weather Forecast API"}

app.include_router(weather_router, prefix="/api/weather")

if __name__ == "__main__":
    # Running with 'python -m uvicorn server.main:app' is recommended
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)