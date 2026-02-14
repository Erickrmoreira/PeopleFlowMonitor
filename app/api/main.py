from fastapi import FastAPI, Depends
from app.analytics.statistics import StatsAnalyzer
import uvicorn

app = FastAPI(title="PeopleFlowMonitor API", version="1.0.0")


def get_stats_analyzer() -> StatsAnalyzer:
    """Dependency injection for analytics service."""
    return StatsAnalyzer()


@app.get("/", tags=["System"])
async def home():
    return {"status": "online", "service": "PeopleFlowMonitor API"}


@app.get("/stats", tags=["Analytics"])
async def get_stats(stats: StatsAnalyzer = Depends(get_stats_analyzer)):
    """Returns today's people flow metrics."""
    report = stats.get_daily_report()
    return {
        "today": report,
        "unit": "people"
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Lightweight endpoint for infrastructure probes."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=False)
