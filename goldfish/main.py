from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from goldfish.api.v1 import item, sales_order, accounts, stock, crm, manufacturing, auth
from goldfish.utils.exceptions import GoldfishException

app = FastAPI()

app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(item.router, prefix="/api/v1", tags=["items"])
app.include_router(sales_order.router, prefix="/api/v1", tags=["sales_orders"])
app.include_router(accounts.router, prefix="/api/v1", tags=["accounts"])
app.include_router(stock.router, prefix="/api/v1", tags=["stock"])
app.include_router(crm.router, prefix="/api/v1", tags=["crm"])
app.include_router(manufacturing.router, prefix="/api/v1", tags=["manufacturing"])

@app.exception_handler(GoldfishException)
async def goldfish_exception_handler(request: Request, exc: GoldfishException):
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )

@app.get("/")
async def root():
    return {"message": "Welcome to Goldfish API"}