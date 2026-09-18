from fastapi import FastAPI

app = FastAPI(title="NRG Grid API", version="0.1.0")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "NRG Grid API"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
