import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

from api.weather import router as weather_router
from scheduler.jobs import scheduler

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
