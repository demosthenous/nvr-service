import sqlite3
from uuid import UUID
from app.models import NVR, Camera, CameraKind

class NotFoundError(Exception): pass
class ConflictError(Exception): pass

class ConfirmationRequiredError(Exception):
    """Raised when deleting an NVR would also affect cameras still linked to it."""
    def __init__(self, message: str, cameras: list[Camera]):
        super().__init__(message)
        self.cameras = cameras


def create_nvr(conn: sqlite3.Connection, nvr: NVR) -> NVR:
    try:
        conn.execute(
            "INSERT INTO nvrs (serial_number, make, model, maximum_input_channels)"
            " VALUES (?, ?, ?, ?)",
            (str(nvr.serial_number), nvr.make, nvr.model, nvr.maximum_input_channels),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        raise ConflictError(f"NVR {nvr.serial_number} already exists") from exc
    return nvr


def delete_nvr(conn: sqlite3.Connection, serial_number: UUID, confirm: bool = False) -> None:
    exists = conn.execute(
        "SELECT 1 FROM nvrs WHERE serial_number = ?", (str(serial_number),)
    ).fetchone()
    if exists is None:
        raise NotFoundError(f"NVR {serial_number} not found")

    linked = list_cameras(conn, nvr_uuid=serial_number)
    if linked and not confirm:
        names = ", ".join(f"{c.make} {c.model}" for c in linked)
        raise ConfirmationRequiredError(
            f"{len(linked)} camera(s) are linked to this NVR ({names}). "
            "Are you sure you want to delete it?",
            linked,
        )

    conn.execute("DELETE FROM nvrs WHERE serial_number = ?", (str(serial_number),))
    conn.commit()


def create_camera(conn: sqlite3.Connection, camera: Camera) -> Camera:
    nvr_row = conn.execute(
        "SELECT * FROM nvrs WHERE serial_number = ?", (str(camera.nvr_uuid),)
    ).fetchone()
    if nvr_row is None:
        raise NotFoundError(f"NVR {camera.nvr_uuid} not found; cannot attach camera")

    current_count = conn.execute(
        "SELECT COUNT(*) AS n FROM cameras WHERE nvr_uuid = ?", (str(camera.nvr_uuid),)
    ).fetchone()["n"]
    if current_count >= nvr_row["maximum_input_channels"]:
        raise ConflictError(
            f"NVR {camera.nvr_uuid} has reached its maximum of "
            f"{nvr_row['maximum_input_channels']} input channels; cannot attach another camera"
        )
    try:
        conn.execute(
            "INSERT INTO cameras (serial_number, make, model, kind, location, nvr_uuid)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (str(camera.serial_number), camera.make, camera.model,
             camera.kind.value, camera.location, str(camera.nvr_uuid)),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        raise ConflictError(f"Camera {camera.serial_number} already exists") from exc
    return camera


def delete_camera(conn: sqlite3.Connection, serial_number: UUID) -> None:
    cur = conn.execute("DELETE FROM cameras WHERE serial_number = ?", (str(serial_number),))
    conn.commit()
    if cur.rowcount == 0:
        raise NotFoundError(f"Camera {serial_number} not found")


def list_nvrs(conn: sqlite3.Connection) -> list[NVR]:
    return [NVR(**dict(row)) for row in conn.execute("SELECT * FROM nvrs ORDER BY make, model")]


def list_cameras(
    conn: sqlite3.Connection,
    nvr_uuid: UUID | None = None,
    location: str | None = None,
    kind: CameraKind | None = None,
) -> list[Camera]:
    """Backs workflows 3, 4 and 5: each filter is an optional WHERE clause."""
    clauses, params = [], []
    if nvr_uuid is not None:
        clauses.append("nvr_uuid = ?"); params.append(str(nvr_uuid))
    if location is not None:
        clauses.append("location = ?"); params.append(location)
    if kind is not None:
        clauses.append("kind = ?"); params.append(kind.value)

    sql = "SELECT * FROM cameras"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY location, make, model"

    return [Camera(**dict(row)) for row in conn.execute(sql, params)]