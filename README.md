# NVR & Camera Metadata Service

A small FastAPI service for tracking NVRs (Network Video Recorders) and the
cameras attached to them. It exposes a REST API to create and delete NVRs
and cameras, and to list cameras filtered by NVR, location, and/or kind.
Data is persisted to a local SQLite file, so it survives service restarts.

## Design decisions

- **SQLite.** The brief only requires that data survive restarts and that
  the service run on a laptop with no extra setup. SQLite is a single file
  on disk with no server process to install, configure, or keep running —
  it satisfies both requirements with the least moving parts. Anything
  bigger (Postgres, etc.) would add operational weight the brief doesn't
  ask for.

- **Layered code (`db` / `models` / `repository` / `main`).**
  - `db.py` owns the schema and the raw connection (including turning on
    SQLite foreign key enforcement, which is off by default).
  - `models.py` owns validation and shape via Pydantic — blank strings,
    invalid enum values, and malformed UUIDs are rejected before any SQL
    runs.
  - `repository.py` owns the business rules that don't belong in either
    layer above: uniqueness, capacity limits, the delete-confirmation
    flow. It raises plain domain exceptions (`NotFoundError`,
    `ConflictError`, `ConfirmationRequiredError`) with no knowledge of
    HTTP.
  - `main.py` wires it together and is the only layer that knows about
    HTTP — it maps those domain exceptions to status codes via FastAPI
    exception handlers.

  This keeps SQL, validation, and business rules independently testable
  and means the repository layer could be swapped for a different backing
  store without touching validation or routing.

- **One filterable `GET /cameras` instead of three endpoints.** The brief
  asks for three read workflows: cameras by NVR, by location, and by
  kind. These are the same query shape with a different `WHERE` clause,
  so they're served by one endpoint (`GET /cameras`) with three optional
  query parameters (`nvr_uuid`, `location`, `kind`) that AND together.
  This also lets a caller combine filters (e.g. thermal cameras on one
  NVR) for free, which three separate endpoints wouldn't offer without
  extra plumbing.

- **Deleting an NVR cascades to its cameras, but asks first.** The schema
  defines `cameras.nvr_uuid` with `ON DELETE CASCADE`, so at the database
  level removing an NVR also removes its cameras — there's no such thing
  as an orphaned camera row. But an unconfirmed cascade is a good way to
  silently lose data a caller didn't realize was linked, so the API layer
  adds a confirmation step in front of it: deleting an NVR with cameras
  still attached returns `409` with the list of affected cameras instead
  of deleting anything, and the caller must resend the request with
  `?confirm=true` to actually cascade the delete. Deleting an NVR with no
  cameras attached needs no confirmation.

## Data model

**NVR**

| Field                    | Type              |
|---------------------------|-------------------|
| `serial_number`            | UUID (primary key) |
| `make`                      | string            |
| `model`                     | string            |
| `maximum_input_channels`    | integer (> 0)     |

**Camera**

| Field           | Type                                                |
|------------------|------------------------------------------------------|
| `serial_number`   | UUID (primary key)                                    |
| `make`             | string                                                |
| `model`            | string                                                |
| `kind`              | enum: `electro-optical`, `thermal`, `infrared`        |
| `location`          | string                                                |
| `nvr_uuid`           | UUID (foreign key → `nvrs.serial_number`)             |

Each camera references the NVR it's attached to via `nvr_uuid`, a foreign
key to `nvrs.serial_number`, with `ON DELETE CASCADE`.

## Setup

```bash
git clone https://github.com/demosthenous/nvr-service.git
cd nvr-service

python3 -m venv .venv

# macOS/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

## Running

```bash
uvicorn app.main:app --reload
```

Interactive API docs (Swagger UI) are available at
`http://127.0.0.1:8000/docs`.

To seed the database with the sample data:

```bash
python seed.py
```

The service also serves a minimal web UI at `http://127.0.0.1:8000/` for
adding and deleting NVRs and cameras. **This is an extra beyond the
required scope** — the API above is the graded surface.

## Running the tests

```bash
pytest
```

`tests/tests_api.py` exercises all five required workflows end-to-end
through the HTTP API (`TestClient`, in-memory temp SQLite files): creating
NVRs and cameras, deleting an NVR (both the confirmation prompt and the
confirmed cascade), listing cameras filtered by NVR/location/kind, plus
validation errors, capacity limits, duplicate-serial conflicts, and a test
that data written before a simulated restart is still there after.

## API reference

| Method | Path                        | Description                                                        |
|--------|-----------------------------|----------------------------------------------------------------------|
| POST   | `/nvrs`                     | Create an NVR                                                        |
| GET    | `/nvrs`                     | List all NVRs                                                        |
| DELETE | `/nvrs/{serial_number}`     | Delete an NVR; `?confirm=true` required if cameras are attached (cascades to them) |
| POST   | `/cameras`                  | Create a camera on an NVR (rejected if the NVR is unknown or full)  |
| GET    | `/cameras`                  | List cameras, optionally filtered by `nvr_uuid`, `location`, `kind` |
| DELETE | `/cameras/{serial_number}`  | Delete a camera                                                      |

Base URL below is `http://127.0.0.1:8000`.

**Create an NVR**

```bash
curl -X POST http://127.0.0.1:8000/nvrs \
  -H "Content-Type: application/json" \
  -d '{"make": "Hanwha Vision", "model": "QRN-1610S", "maximum_input_channels": 16}'
```

**Create a camera on that NVR**

```bash
curl -X POST http://127.0.0.1:8000/cameras \
  -H "Content-Type: application/json" \
  -d '{"make": "Hikvision", "model": "DS-2CD2T83G2-4I", "kind": "electro-optical",
       "location": "Building A", "nvr_uuid": "<nvr serial_number from above>"}'
```

**Delete (with cascade confirmation)**

```bash
# First attempt on an NVR with cameras attached returns 409:
curl -i -X DELETE http://127.0.0.1:8000/nvrs/<nvr serial_number>

# Resend with confirm=true to proceed; cascades to its cameras:
curl -i -X DELETE "http://127.0.0.1:8000/nvrs/<nvr serial_number>?confirm=true"
```

**Cameras by NVR**

```bash
curl "http://127.0.0.1:8000/cameras?nvr_uuid=<nvr serial_number>"
```

**Cameras by location**

```bash
curl "http://127.0.0.1:8000/cameras?location=Building%20A"
```

**Cameras by kind**

```bash
curl "http://127.0.0.1:8000/cameras?kind=thermal"
```

**Combining filters** (location + kind, both narrowing the same result set)

```bash
curl "http://127.0.0.1:8000/cameras?location=Building%20A&kind=thermal"
```

## Error handling

| Status | When                                                                                     |
|--------|--------------------------------------------------------------------------------------------|
| `422`  | Request body fails Pydantic validation — blank `make`/`model`/`location`, non-positive `maximum_input_channels`, an invalid `kind`, or a malformed UUID |
| `404`  | The NVR or camera referenced by the path doesn't exist; also returned when creating a camera against an `nvr_uuid` that doesn't exist |
| `409`  | A duplicate `serial_number` is submitted for an NVR or camera; a camera is created against an NVR that's already at `maximum_input_channels`; or an NVR with cameras attached is deleted without `?confirm=true` (the response body includes the affected cameras) |

## Notes and possible extensions

- Two camera serial numbers in `sample_nvr_camera_data.json` are not valid
  UUIDs — they start with `g` and `h`, which aren't hex characters. As a
  result, `python seed.py` seeds all three NVRs and the first three
  cameras, then crashes with a Pydantic `uuid_parsing` error on the fourth
  camera record; the fifth is never attempted. This is a defect in the
  sample data file itself, not in the service's validation, which is
  correctly rejecting it. Fixing the two serials (or making `seed.py`
  skip bad records and report them) would resolve it.
- There's no authentication/authorization — out of scope for this
  exercise, but would be required before running this anywhere real.
- No update (`PUT`/`PATCH`) endpoints — only the create/list/delete
  workflows in the brief are implemented.
- List endpoints have no pagination; fine at sample-data scale, would
  need it under real data volume.
- SQLite serializes writes to a single file, which is the right tradeoff
  for a single-instance take-home but wouldn't scale to concurrent
  multi-writer load — a real deployment would move to Postgres at that
  point.
