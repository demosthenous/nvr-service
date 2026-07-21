import json
import logging
import sqlite3
from pathlib import Path
from pydantic import ValidationError
from app import repository as repo
from app.models import NVR, Camera

logger = logging.getLogger(__name__)

SAMPLE_DATA_PATH = Path(__file__).resolve().parent.parent / "sample_nvr_camera_data.json"


def seed_sample_data(conn: sqlite3.Connection, path: Path = SAMPLE_DATA_PATH) -> None:
    """Load the sample NVRs/cameras into `conn`.

    Safe to call on every app startup: records that already exist (matched
    by serial_number) are skipped rather than raising, and records that fail
    validation are skipped with a logged warning instead of aborting the rest
    of the load.
    """
    data = json.loads(path.read_text())

    for raw in data["nvrs"]:
        try:
            repo.create_nvr(conn, NVR(**raw))
        except (ValidationError, repo.ConflictError) as exc:
            logger.warning("Skipping sample NVR %s: %s", raw.get("serial_number"), exc)

    for raw in data["cameras"]:
        try:
            repo.create_camera(conn, Camera(**raw))
        except (ValidationError, repo.ConflictError, repo.NotFoundError) as exc:
            logger.warning("Skipping sample camera %s: %s", raw.get("serial_number"), exc)
