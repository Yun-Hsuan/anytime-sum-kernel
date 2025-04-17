from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils, scraper, dev, article, scheduler, fetch_db
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(private.router)
api_router.include_router(scraper.router, prefix="/scrapers", tags=["scrapers"])
api_router.include_router(article.router, prefix="/articles", tags=["articles"])
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"])
api_router.include_router(fetch_db.router, prefix="/fetch", tags=["fetch"])

# 只在本地開發環境中包含開發者路由
if settings.ENVIRONMENT == "local":
    api_router.include_router(dev.router)
    api_router.include_router(private.router)
