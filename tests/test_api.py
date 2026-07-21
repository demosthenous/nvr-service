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
def test_deleting_nvr_with_linked_cameras_requires_confirmation(client):
    client.post("/nvrs", json=make_nvr())
    client.post("/cameras", json=make_cam())

    r = client.delete(f"/nvrs/{NVR_ID}")
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["confirmation_required"] is True
    assert "camera" in detail["message"].lower()
    assert len(detail["cameras"]) == 1

    # camera must still exist; nothing was deleted
    assert len(client.get("/cameras").json()) == 1

def test_deleting_nvr_cascades_to_cameras_when_confirmed(client):
    client.post("/nvrs", json=make_nvr())
    client.post("/cameras", json=make_cam())
    assert client.delete(f"/nvrs/{NVR_ID}", params={"confirm": "true"}).status_code == 204
    assert client.get("/cameras").json() == []

def test_deleting_nvr_without_cameras_needs_no_confirmation(client):
    client.post("/nvrs", json=make_nvr())
    assert client.delete(f"/nvrs/{NVR_ID}").status_code == 204

def test_camera_rejected_when_nvr_at_max_capacity(client):
    client.post("/nvrs", json=make_nvr(maximum_input_channels=1))
    assert client.post("/cameras", json=make_cam()).status_code == 201
    r = client.post("/cameras", json=make_cam(serial_number="22222222-2222-2222-2222-222222222222"))
    assert r.status_code == 409
    assert "maximum" in r.json()["detail"].lower()

def test_list_nvrs(client):
    client.post("/nvrs", json=make_nvr())
    r = client.get("/nvrs")
    assert r.status_code == 200
    assert [n["serial_number"] for n in r.json()] == [NVR_ID]

def test_blank_make_rejected(client):
    r = client.post("/nvrs", json=make_nvr(make="   "))
    assert r.status_code == 422

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

def test_seed_on_startup_loads_sample_records(tmp_path):
    client = TestClient(create_app(db_path=tmp_path / "seeded.db", seed=True))
    nvrs = client.get("/nvrs").json()
    cameras = client.get("/cameras").json()
    assert len(nvrs) == 3
    assert len(cameras) == 5

def test_seeding_twice_is_idempotent(tmp_path):
    path = tmp_path / "reseeded.db"
    TestClient(create_app(db_path=path, seed=True))
    client = TestClient(create_app(db_path=path, seed=True))  # simulate a second startup
    assert len(client.get("/nvrs").json()) == 3
    assert len(client.get("/cameras").json()) == 5