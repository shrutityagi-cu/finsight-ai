from fastapi import FastAPI

from app.api.v1.routes import (
    auth,
    historical_prices,
    market_symbols,
    portfolios,
    predictions,
    watchlists,
    dashboard,
)
from app.api.v1.routes import health as health_routes

from app.config.settings import settings


app = FastAPI(


    title=settings.project_name,
    version="0.1.0",
    debug=settings.debug,
    description="Production-ready backend scaffold for FinSight AI.",
)

app.include_router(health_routes, prefix=settings.api_v1_prefix)


app.include_router(auth, prefix=settings.api_v1_prefix)
app.include_router(portfolios, prefix=settings.api_v1_prefix)
app.include_router(watchlists, prefix=settings.api_v1_prefix)
app.include_router(historical_prices, prefix=settings.api_v1_prefix)
app.include_router(market_symbols, prefix=settings.api_v1_prefix)
app.include_router(predictions, prefix=settings.api_v1_prefix)
app.include_router(dashboard, prefix=settings.api_v1_prefix)



