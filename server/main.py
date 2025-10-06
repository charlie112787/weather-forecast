import sys
import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

# --- Add project root to Python path ---
# Ensure the repository root is on sys.path so 'server.*' imports work consistently
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
# --- End of path modification ---

from server.api.weather import router as weather_router
import asyncio
from server.scheduler import jobs
from server.scheduler.jobs import scheduler

load_dotenv()

app = FastAPI(
    title="Weather Forecast API",
    description="API for providing weather forecasts and sending notifications.",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    # Trigger the data fetching job to run immediately in the background
    print("Triggering initial data fetch job on startup...")
    asyncio.create_task(jobs.fetch_data_job())
    
    # Start the scheduler for subsequent hourly runs
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