from fastapi import FastAPI


app = FastAPI(title="Warehouse Management System")


@app.get("/health")
def health_check():
    return {"status": "ok"}
