from pathlib import Path
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException, Query
from app import db, repository as repo
from app.models import NVR, Camera, CameraKind

def create_app(db_path: Path = db.DEFAULT_DB_PATH) -> FastAPI:
    app = FastAPI(title="NVR & Camera Metadata Service")

    conn = db.get_connection(db_path)
    db.init_db(conn)
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

    @app.post("/nvrs", response_model=NVR, status_code=201)
    def create_nvr(nvr: NVR, conn=Depends(get_db)):
        return repo.create_nvr(conn, nvr)

    @app.delete("/nvrs/{serial_number}", status_code=204)
    def delete_nvr(serial_number: UUID, conn=Depends(get_db)):
        repo.delete_nvr(conn, serial_number)

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

    return app

app = create_app()