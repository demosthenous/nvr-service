# NVR & Camera Metadata Service

A small FastAPI service for tracking NVRs (Network Video Recorders) and the
cameras attached to them, backed by SQLite. Includes a minimal web UI for
adding and deleting NVRs and cameras.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
uvicorn app.main:app --reload
```

The web UI is served at `http://127.0.0.1:8000/`. Interactive API docs
(Swagger UI) are available at `http://127.0.0.1:8000/docs`.

Optionally seed the database with sample data:

```bash
python seed.py
```

## Data model

- **NVR** — `serial_number` (UUID), `make`, `model`, `maximum_input_channels`
- **Camera** — `serial_number` (UUID), `make`, `model`, `kind`
  (`electro-optical` / `thermal` / `infrared`), `location`, `nvr_uuid`

Each camera belongs to exactly one NVR. An NVR cannot have more cameras
attached than its `maximum_input_channels`.

## API

| Method | Path                    | Description                                   |
|--------|-------------------------|------------------------------------------------|
| POST   | `/nvrs`                 | Create an NVR                                  |
| GET    | `/nvrs`                 | List NVRs                                      |
| DELETE | `/nvrs/{serial_number}` | Delete an NVR (see confirmation note below)    |
| POST   | `/cameras`              | Create a camera (rejects if its NVR is full)   |
| GET    | `/cameras`              | List cameras, filterable by `nvr_uuid`, `location`, `kind` |
| DELETE | `/cameras/{serial_number}` | Delete a camera                             |

Deleting an NVR that still has cameras attached returns `409` with a
confirmation message and the list of affected cameras, instead of deleting
immediately. Resend the request with `?confirm=true` to proceed, which
cascades the delete to those cameras.

## Testing

```bash
pytest
```
