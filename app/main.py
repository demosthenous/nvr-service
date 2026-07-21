from pathlib import Path
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app import db, repository as repo
from app.models import NVR, Camera, CameraKind
from app.seeding import seed_sample_data

STATIC_DIR = Path(__file__).resolve().parent / "static"

def create_app(db_path: Path = db.DEFAULT_DB_PATH, seed: bool = False) -> FastAPI:
    app = FastAPI(title="NVR & Camera Metadata Service")

    conn = db.get_connection(db_path)
    db.init_db(conn)
    if seed:
        seed_sample_data(conn)
    conn.close()

    def get_db():
        conn = db.get_connection(db_path)
        try:
            yield conn
        finally:
            conn.close()

    @app.exception_handler(repo.NotFoundError)
    async def _not_found(_req, exc):
        raise HTTPException(status_code=404, detail=str(exc))

    @app.exception_handler(repo.ConflictError)
    async def _conflict(_req, exc):
        raise HTTPException(status_code=409, detail=str(exc))

    @app.exception_handler(repo.ConfirmationRequiredError)
    async def _confirmation_required(_req, exc: repo.ConfirmationRequiredError):
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "confirmation_required": True,
                "cameras": [c.model_dump(mode="json") for c in exc.cameras],
            },
        )

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.post("/nvrs", response_model=NVR, status_code=201)
    def create_nvr(nvr: NVR, conn=Depends(get_db)):
        return repo.create_nvr(conn, nvr)

    @app.get("/nvrs", response_model=list[NVR])
    def list_nvrs(conn=Depends(get_db)):
        return repo.list_nvrs(conn)

    @app.delete("/nvrs/{serial_number}", status_code=204)
    def delete_nvr(serial_number: UUID, confirm: bool = Query(False), conn=Depends(get_db)):
        repo.delete_nvr(conn, serial_number, confirm=confirm)

    @app.post("/cameras", response_model=Camera, status_code=201)
    def create_camera(camera: Camera, conn=Depends(get_db)):
        return repo.create_camera(conn, camera)

    @app.delete("/cameras/{serial_number}", status_code=204)
    def delete_camera(serial_number: UUID, conn=Depends(get_db)):
        repo.delete_camera(conn, serial_number)

    @app.get("/cameras", response_model=list[Camera])
    def list_cameras(
        conn=Depends(get_db),
        nvr_uuid: UUID | None = Query(None),
        location: str | None = Query(None),
        kind: CameraKind | None = Query(None),
    ):
        """Workflows 3-5: filter cameras by NVR, location and/or kind."""
        return repo.list_cameras(conn, nvr_uuid=nvr_uuid, location=location, kind=kind)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app

app = create_app(seed=True)