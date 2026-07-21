import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as tmp:
        yield TestClient(create_app(db_path=Path(tmp) / "test.db"))

NVR_ID = "a3f5e8d1-2c4b-4a9e-8f3d-1b5c7e9f2a4d"

def make_nvr(**kw):
    return {"serial_number": NVR_ID, "make": "Hanwha", "model": "QRN-1610S",
            "maximum_input_channels": 16, **kw}

def make_cam(**kw):
    return {"make": "Hikvision", "model": "DS-2CD2T83G2-4I", "kind": "electro-optical",
            "location": "Building A", "nvr_uuid": NVR_ID, **kw}

# Workflow 1
def test_create_nvr_and_camera(client):
    assert client.post("/nvrs", json=make_nvr()).status_code == 201
    assert client.post("/cameras", json=make_cam()).status_code == 201

def test_invalid_kind_rejected(client):
    client.post("/nvrs", json=make_nvr())
    assert client.post("/cameras", json=make_cam(kind="x-ray")).status_code == 422

def test_camera_on_unknown_nvr_rejected(client):
    r = client.post("/cameras", json=make_cam(nvr_uuid="11111111-1111-1111-1111-111111111111"))
    assert r.status_code == 404

# Workflow 2
def test_deleting_nvr_cascades_to_cameras(client):
    client.post("/nvrs", json=make_nvr())
    client.post("/cameras", json=make_cam())
    assert client.delete(f"/nvrs/{NVR_ID}").status_code == 204
    assert client.get("/cameras").json() == []

# Workflows 3, 4, 5
def test_filter_by_kind(client):
    client.post("/nvrs", json=make_nvr())
    client.post("/cameras", json=make_cam(kind="thermal"))
    client.post("/cameras", json=make_cam(kind="infrared"))
    kinds = [c["kind"] for c in client.get("/cameras", params={"kind": "thermal"}).json()]
    assert kinds == ["thermal"]

def test_data_survives_restart(tmp_path):
    path = tmp_path / "persist.db"
    c1 = TestClient(create_app(db_path=path))
    c1.post("/nvrs", json=make_nvr())
    c2 = TestClient(create_app(db_path=path))   # simulate a restart
    assert len(c2.get("/cameras").json()) == 0
    assert c2.post("/cameras", json=make_cam()).status_code == 201  # NVR still there