# DartaLink

**Digital Administrative Request and Document Workflow Management System** for a Nepal Telecom-style
organisation. It digitises the paper trail of an office: request → section verification → **Darta**
(inward registration) → forwarding → review (recommendation, **Tippani**, **Tok Aadesh**) →
approval / rejection → **Chalani** (outward dispatch) → completion, with a full audit trail.

Stack: Python · Django · Django REST Framework · PostgreSQL · python-dotenv · drf-spectacular (OpenAPI/Swagger) ·
HTML5 + custom CSS + vanilla JavaScript (no frontend frameworks).

---------------------------------------------------------------------------

## 1. Quick start (Windows PowerShell)

```powershell
# 0. unzip, then open PowerShell in the project folder
Set-ExecutionPolicy -Scope Process Bypass        # allow scripts for this window only

# Option A - one command, local SQLite (fastest demo)
.\setup.ps1 -Sqlite

# Option B - PostgreSQL
psql -U postgres -c "CREATE DATABASE dartalink;"
copy .env.example .env                            # then edit DB_USER / DB_PASSWORD
.\setup.ps1
```

`setup.ps1` creates `.venv`, installs requirements, writes `.env` with a random secret key, generates migrations,
migrates, loads demo data and starts the server at <http://127.0.0.1:8000/>.

Manual equivalent:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations accounts requests_app workflow documents notifications
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Run the tests: `.\run_tests.ps1` (or `python manage.py test`). With PostgreSQL the DB user needs `CREATEDB`;
with `DB_ENGINE=sqlite` no extra setup is needed.

| URL | What |
|---|---|
| `/` | Role-specific dashboard (sign in first) |
| `/api/docs/` | Swagger UI |
| `/api/schema/` | OpenAPI 3 schema |
| `/admin/` | Django admin (system management only; the main UI is the app itself) |

## 2. Demo accounts

Every demo user has the password in `DEMO_PASSWORD` (default `DartaLink@2026`). You can sign in with the
username **or** the Staff ID.

| Username | Staff ID | Role |
|---|---|---|
| `admin` | NTC-SA-001 | System Administrator |
| `karyalaya` | NTC-KP-001 | Karyalaya Pramukh (Office Head - final approval) |
| `prabidhik` | NTC-PP-001 | Prabidhik Pramukh |
| `lekha` | NTC-LP-001 | Lekha Pramukh |
| `rajaswa` / `budget` / `itchief` | NTC-RS-001 / NTC-BS-001 / NTC-IT-001 | Section Pramukhs |
| `darta1`, `darta2` | NTC-DT-001, -002 | Darta staff |
| `chalani1`, `chalani2` | NTC-CH-001, -002 | Chalani staff |
| `it_staff`, `it_staff2`, `rev_staff`, `tech_staff` | NTC-IT-002.., NTC-RS-002, NTC-PP-002 | Section staff (requesters) |

`seed_demo` also creates ~12 sample requests that sit in every workflow state (draft, awaiting verification,
awaiting Darta, returned, registered, forwarded, under review with recommendation/tippani, approved, dispatched,
completed, rejected). Re-run with `--reset` to rebuild them.

## 3. The workflow

```
Staff ──submit──▶ SUBMITTED ──verify (section Pramukh)──▶ VERIFIED ──register (Darta)──▶ REGISTERED
   ▲                  │return                                │return                         │forward
   │ edit & resubmit  ▼                                      ▼                               ▼
   └──────────────── RETURNED ◀──────── return ──── FORWARDED ⇄ UNDER_REVIEW  (any authority: recommend,
                                                         │            tippani, forward; Karyalaya Pramukh:
                                                         │            Tok Aadesh)
                                         approve (KP) ───┴─── reject (KP) ──▶ REJECTED
                                              ▼
                         APPROVED ──process──▶ PROCESSING ──dispatch (Chalani no.)──▶ DISPATCHED ──▶ COMPLETED
```

* A request submitted by a Pramukh skips section verification.
* Darta / Chalani numbers (`DARTA-2083/84-0001`, `CHALANI-2083/84-0001`) use per-fiscal-year counters. A request
  keeps its Darta number if it is returned and re-registered. Request numbers look like `DL-REQ-2026-00001`.
* What a user may do is decided server-side by `workflow/services.py` (action table + `perform()`), never by the UI.
  Fields are stage-driven: only the requester can edit, and only in Draft/Returned; Darta/Chalani numbers are assigned
  by the system at the right stage.
* Every action is written to `WorkflowLog` (shown as the History timeline and the admin-only Audit log) and creates
  notifications for the people who must act next.

### Who can do what

| Role | Capabilities |
|---|---|
| Section staff | Create/edit own drafts, submit, cancel, upload documents, see own requests |
| Section Pramukh | Verify / return / reject requests of **their own section**; act on requests forwarded to them (recommend, tippani, forward, return) |
| Darta staff | Register verified requests, forward them to an authority, return |
| Karyalaya Pramukh | Everything an authority can do **plus** Tok Aadesh, approve, reject; sees all registered files |
| Chalani staff | See approved files; process, dispatch (assign Chalani no.), complete |
| System Administrator | Manage users, departments and see everything + audit log (cannot create requests) |

Visibility rules (`requests_app/selectors.py`) are applied in every list, detail, download and API call, so a
user never sees another section's requests; an invisible request returns **404**.

## 4. Project layout

```
config/            settings (env driven), root urls, wsgi/asgi
accounts/          Department, User (Staff ID, role), StaffProfile, auth + admin screens, seed_demo command
requests_app/      AdministrativeRequest, numbering, visibility selectors, search/filter, request screens
workflow/          state machine (services.py), WorkflowLog, Annotation, audit-log screen
documents/         Document model, private storage, validation, secure upload/download/delete
notifications/     Notification model, service, bell/list views
dashboard/         role/section dashboards
core/              context processor (nav, bell), template tags, error handlers, test helpers
api/               DRF serializers, viewsets, router, OpenAPI endpoints
templates/ static/ HTML templates, custom CSS (CSS variables), vanilla JS, logo
```

## 5. REST API (`/api/`)

Session-authenticated, paginated (10/page), searchable and documented at `/api/docs/`.

`departments`, `users` (+ `/me/`), `requests` (filters: `q status category priority department scope date_from
date_to`; actions: `POST /{id}/actions/`, `GET /{id}/available-actions/`, `GET /{id}/timeline/`), `workflow-logs`,
`annotations`, `documents` (multipart upload + `/download/`), `notifications` (`mark-read`, `mark-all-read`,
`unread-count`). Permissions mirror the web UI because both call the same services and selectors.

Example (after signing in through the browser session, or with `requests.Session`):

```json
POST /api/requests/42/actions/
{"action": "forward", "to_department": 3, "remarks": "Please review"}
```

## 6. Security notes

* Django CSRF on every form and on the notification `fetch` calls; session cookies `HttpOnly`, `SameSite=Lax`,
  8-hour sliding expiry; HSTS/secure cookies/SSL redirect automatically when `DJANGO_DEBUG=False`.
* Secrets and DB credentials live in `.env` (never committed); the app refuses to start without
  `DJANGO_SECRET_KEY` when debug is off.
* Authorization is enforced in views, selectors, the workflow engine and the API; object-level access returns 404.
* Uploads: extension allow-list, size limit (`MAX_UPLOAD_MB`), magic-byte check for PDF/PNG/JPEG/Office files,
  random on-disk names, stored in `private_media/` which is **not** a served path; downloads stream through an
  authenticated, permission-checked view with `Content-Disposition: attachment` and `nosniff`.
* Password validators on, change-password screen, inactive users cannot sign in or act.
* Workflow email notifications are sent to `WORKFLOW_NOTIFICATION_EMAIL` after each request creation or
  workflow operation. The development default is `poksamir6@gmail.com`; configure the SMTP variables in
  `.env` before using a real mailbox. Gmail requires an app password when two-factor authentication is enabled.
* System administrators can use **Administration → Send message** to send a targeted in-app and email message
  to one or more active employees. The message is retained as a direct-message record for auditability.
* For production also put the app behind HTTPS, set `DJANGO_ALLOWED_HOSTS`, run `collectstatic`, and serve with
  gunicorn/uvicorn + a reverse proxy (or WhiteNoise).

## 7. Branding / logo

The UI uses the supplied Nepal Telecom artwork at `static/img/nt-logo.png` by default. To use another approved
brand asset, place it in `static/img/` and set `BRAND_LOGO=img/your-logo.png` in `.env`. The header, login page
and error pages scale it to a fixed height with `width:auto`, so any aspect ratio stays aligned.

## 8. Tests

`python manage.py test` runs about 90 tests across the apps: authentication & authorization, Staff ID generation,
full request lifecycle and every forbidden transition, Darta/Chalani numbering and queues, visibility isolation,
search/filter/pagination, documents (validation, access, deletion), notifications and the REST API
(including schema generation).

## 9. Design

Warm paper background, Apple-style system type stack (SF Pro / Segoe UI fallbacks, Devanagari-safe), Nepal Telecom
blue and red used sparingly, CSS variables for all colours, restrained motion that respects
`prefers-reduced-motion`, visible keyboard focus, skip-link, ARIA on modals/menus (Escape closes, focus is trapped
in modals), responsive off-canvas sidebar on small screens.
