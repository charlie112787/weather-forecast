import sys
import os

# Add the project root to the Python path to resolve module import issues
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from api.weather import router as weather_router
from api.fcm import fcm_router # 引入新的 fcm_router
import asyncio
from scheduler import jobs
from scheduler.jobs import scheduler

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
app.include_router(fcm_router) # 包含 fcm_router

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8100, reload=True)
