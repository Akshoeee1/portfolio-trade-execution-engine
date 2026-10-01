import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import auth, brokers, execution, notifications
from app.store.memory_store import InMemoryStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Kalpi Portfolio Trade Execution Engine")
app.state.store = InMemoryStore()

app.include_router(auth.router)
app.include_router(brokers.router)
app.include_router(execution.router)
app.include_router(notifications.router)

app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI"}
