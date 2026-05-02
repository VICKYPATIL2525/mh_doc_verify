# mh_doc_verify — Project Architecture & Flow Diagrams

This document is the single source of truth for understanding the **Doctor Document Verification Portal** — one module inside the larger RBAC system for the **Mental Space** platform. The portal is used exclusively by internal staff (assigned by the platform admin) to review, approve, or reject doctor applications. Doctors submit their applications and documents on a separate platform; this portal pulls that data and presents it for review.

All diagrams use Mermaid flowchart syntax. The focus is on **how data and control flow through the system**.

---

## 1. Folder & File Structure

The project has two layers — the Django **project config** (`app_doc_verify/`) which holds settings, main URL router, and the login view, and the **business logic app** (`doc_review/`) which holds all models, views, URLs, email stub, admin registration, and the seed command. Templates, static files, and the simulated GCP media folder live at the project root level alongside both packages.

```mermaid
flowchart TD
    Root["mh_doc_verify/"] --> AppRoot["app_doc_verify/\nDjango project root"]

    AppRoot --> Config["app_doc_verify/\nProject config"]
    AppRoot --> App["doc_review/\nBusiness logic app"]
    AppRoot --> Templates["templates/"]
    AppRoot --> Static["static/"]
    AppRoot --> Media["media/\nSimulated GCP"]
    AppRoot --> DB["db.sqlite3"]

    Config --> S["settings.py"]
    Config --> U["urls.py\nMain router"]
    Config --> V["views.py\nLogin only"]

    App --> M["models.py"]
    App --> AV["views.py"]
    App --> AU["urls.py"]
    App --> AD["admin.py"]
    App --> AE["email.py\nEmail stub"]
    App --> Mig["migrations/\n0001 0002"]
    App --> Mgmt["management/\nseed_data.py"]

    Templates --> TI["index.html\nLogin page"]
    Templates --> TDR["doc_review/\nbase.html\ndashboard.html\napplication_detail.html\nall_comments.html"]

    Static --> SI["index.css"]
    Static --> SDR["doc_review/\nstyle.css"]

    Media --> Docs["doctor_docs/\ndr_amit_sharma/\ndr_priya_nair/\ndr_rohit_desai/"]
```

---

## 2. Database Schema & Relationships

The system has two custom tables — `DoctorApplication` and `Comment`. Both link to Django's built-in `User` table. Staff accounts are created only by the superuser through the `/admin/` panel — no signup flow exists in this portal. `reviewed_by` on `DoctorApplication` uses `SET NULL` so that deleting a staff account never deletes the application record — it just clears the reviewer reference. `Comment` uses `CASCADE` so comments are cleaned up if either the application or the author is deleted.

```mermaid
flowchart LR
    subgraph Builtin["Django Built-in"]
        User["User\n──────────\nid PK\nusername\npassword\nemail\nis_staff\nis_superuser"]
    end

    subgraph Custom["doc_review app"]
        DA["DoctorApplication\n──────────────────\nid PK\nfull_name\nemail\nphone\nspecialization\ndoc_folder\nstatus\nrejection_reason\nreviewed_by FK\nreviewed_at\nsubmitted_at"]

        CM["Comment\n──────────\nid PK\napplication FK\nauthor FK\ntext\ncreated_at"]
    end

    User -->|"reviewed_by\nSET NULL on delete"| DA
    User -->|"author\nCASCADE on delete"| CM
    DA -->|"application\nCASCADE on delete"| CM
```

**Field notes:**
- `doc_folder` stores a relative path today (`doctor_docs/dr_amit_sharma`) — when GCP is connected this becomes a bucket path, no model migration needed
- `rejection_reason` is always stored as an empty string if approved — no null needed
- `Comment` is a separate table so multiple staff can add multiple notes over time as a thread

---

## 3. URL Routing Map

Every HTTP request hits `app_doc_verify/urls.py` first. That file either handles it directly (login, admin, media files) or delegates to `doc_review/urls.py` via `include()`. This two-level routing keeps the project config clean and the app self-contained. The `include()` at the empty path `""` means `doc_review` URLs are at the root — so `/dashboard/` not `/doc-review/dashboard/`.

```mermaid
flowchart TD
    Browser["HTTP Request"] --> Main["app_doc_verify/urls.py\nMain Router"]

    Main -->|"GET POST /"| Login["views.home\nLogin page"]
    Main -->|"/admin/"| Admin["Django Admin\nSuperuser only"]
    Main -->|"/media/..."| Media["Serve files\nfrom media/ folder"]
    Main -->|"include"| App["doc_review/urls.py\nApp Router"]

    App -->|"GET /dashboard/"| V1["views.dashboard"]
    App -->|"GET /application/pk/"| V2["views.application_detail"]
    App -->|"POST /application/pk/"| V2B["views.application_detail\nComment save"]
    App -->|"POST /application/pk/review/"| V3["views.review_application"]
    App -->|"POST /bulk-action/"| V4["views.bulk_action"]
    App -->|"GET /comments/"| V5["views.all_comments"]
    App -->|"GET /export/"| V6["views.export_csv"]
    App -->|"GET /logout/"| V7["views.logout_view"]
```

---

## 4. Authentication & Login Flow

The login page at `/` is the only public URL. Every other view is protected by `@login_required`. If an unauthenticated user visits `/dashboard/` directly, Django redirects them to `/` automatically because `LOGIN_URL = '/'` is set in `settings.py`. The `authenticate()` function hashes the submitted password and compares it to the stored hash — plain text passwords are never stored. On success `login()` writes a session record to the database and sets a `sessionid` cookie in the browser — all subsequent requests carry this cookie and Django validates it automatically.

```mermaid
flowchart TD
    A["Staff visits any URL"] --> B{"Already\nlogged in?"}

    B -->|"Yes\nsession valid"| DASH["Redirect /dashboard/"]

    B -->|"No"| C["Show index.html\nLogin form"]

    C --> D["Staff enters\nusername + password"]

    D --> E["POST /\nwith CSRF token"]

    E --> F["authenticate()\nHash check\nagainst DB"]

    F -->|"No match"| G["messages.error\nRe-render login\nError shown"]

    F -->|"Match"| H["login()\nWrite session to DB\nSet sessionid cookie"]

    H --> I["Redirect 302\n/dashboard/"]

    I --> J["Dashboard loads\nStaff authenticated\nAll views accessible"]

    G --> C
```

---

## 5. Dashboard — Filter, Search, Pagination & Dot Logic

The dashboard is the main working screen. Staff can filter by status, search by name or email, and page through results 20 at a time. All three parameters (`status`, `q`, `page`) work together — changing the filter resets to page 1 while keeping the search, and the CSV export button carries the same params so the download always matches what is on screen. The yellow dot is computed with a single `DISTINCT` query that returns a Python set — the template then does an `O(1)` set lookup per row with no extra DB queries.

```mermaid
flowchart TD
    A["GET /dashboard/\n?status=&q=&page="] --> B{"Login\ncheck"}

    B -->|"No session"| BX["Redirect /"]
    B -->|"OK"| C["DoctorApplication.objects.all()\norder by submitted_at DESC"]

    C --> D{"status\nparam?"}
    D -->|"Yes"| E["filter status=..."]
    D -->|"No"| F["All statuses"]

    E --> G{"search\nparam?"}
    F --> G

    G -->|"Yes"| H["filter name icontains\nOR email icontains"]
    G -->|"No"| I["Unchanged"]

    H --> J["COUNT queries\nfor stat cards\npending approved rejected"]
    I --> J

    J --> K["Paginator\n20 per page"]

    K --> L["DISTINCT query\nComment application IDs\nBuild set of IDs\nwith comments"]

    L --> M["Render dashboard.html"]

    M --> N{"app.pk\nin commented_ids?"}
    N -->|"Yes"| O["Show yellow dot\nnext to name"]
    N -->|"No"| P["No dot"]
```

---

## 6. Application Detail & Comment Flow

The detail page shows everything about one doctor — their info, all submitted documents as clickable links that open in the browser, and the full internal comment thread. The same URL `/application/pk/` handles both GET and POST. On POST it saves the comment and immediately redirects back to GET — this is the PRG pattern (Post-Redirect-Get) which prevents the browser from re-submitting the comment if the staff member refreshes the page. Documents are served from the `media/` folder in development — each file link opens in a new browser tab.

```mermaid
flowchart TD
    A["Staff clicks View\non dashboard row"] --> B["GET /application/3/"]

    B --> C["get_object_or_404\nDoctorApplication pk=3"]

    C --> D["os.listdir\nmedia/doctor_docs/folder"]

    D --> E{"Folder\nexists?"}
    E -->|"Yes"| F["Build file list\nname + URL per file"]
    E -->|"No"| G["doc_files empty\nNo documents found"]

    F --> H["Fetch comments\norder by created_at ASC"]
    G --> H

    H --> I["Render\napplication_detail.html"]

    I --> J{"Staff\naction?"}

    J -->|"Opens document"| K["File opens\nin new browser tab\nvia /media/ URL"]

    J -->|"Submits comment"| L["POST /application/3/\ncomment_text in body"]

    L --> M{"Text\nnon-empty?"}
    M -->|"Empty"| N["Nothing saved"]
    M -->|"Yes"| O["Comment.create\napplication author text"]

    O --> P["Redirect 302\nGET /application/3/\nPRG pattern"]
    N --> P
```

---

## 7. Approve & Reject Decision Flow

The review endpoint `/application/pk/review/` only accepts POST. A direct GET visit redirects back to the detail page. Rejection requires a non-empty reason — submitting without one redirects back with an error and nothing is saved. After every successful decision `send_decision_email()` is called immediately — today it prints to the console, in production it will send a real email to the doctor without any other code changes.

```mermaid
flowchart TD
    A["Staff on detail page\nstatus is pending"] --> B{"Action"}

    B -->|"Approve"| C["Confirm dialog\nin browser"]
    C -->|"Cancel"| A
    C -->|"OK"| D["POST /review/\naction=approve"]

    B -->|"Reject"| E["Textarea appears\nStaff types reason"]
    E --> F["POST /review/\naction=reject\nreason=text"]

    D --> G["Fetch application\nfrom DB"]
    F --> G

    G --> H{"Which\naction?"}

    H -->|"approve"| I["status = approved\nrejection_reason = empty\nreviewed_by = user\nreviewed_at = now"]

    H -->|"reject"| J{"Reason\nprovided?"}
    J -->|"No"| K["Error message\nRedirect back\nNothing saved"]
    J -->|"Yes"| L["status = rejected\nreason = text\nreviewed_by = user\nreviewed_at = now"]

    I --> M["application.save()"]
    L --> M

    M --> N["send_decision_email()\nConsole log today\nReal email later"]

    N --> O["messages.success"]
    O --> P["Redirect /dashboard/\nBadge updated"]
```

---

## 8. Bulk Action Flow

Bulk actions let staff process multiple pending applications in one submission. The checkboxes and toolbar are driven by JavaScript — the toolbar only appears when at least one checkbox is ticked, and shows the count of selected items. Only applications with `status=pending` are processed even if non-pending IDs are submitted — this prevents accidentally overwriting already-decided records. Each application in the loop gets its own email stub call so every doctor gets an individual notification.

```mermaid
flowchart TD
    A["Staff ticks checkboxes\non pending rows"] --> B["JS shows bulk toolbar\nN selected count"]

    B --> C{"Staff clicks"}

    C -->|"Approve Selected"| D["POST /bulk-action/\naction=bulk_approve\nselected_ids list"]

    C -->|"Reject Selected"| E["Modal opens\nStaff types\ncommon reason"]
    E --> F["POST /bulk-action/\naction=bulk_reject\nselected_ids list\ncommon reason"]

    D --> G["Filter queryset\npk in selected_ids\nAND status=pending\nIgnore already decided"]
    F --> G

    G --> H{"Any\nmatches?"}
    H -->|"None"| I["Error message\nRedirect dashboard"]

    H -->|"Found"| J["Loop each\napplication"]
    J --> K["Set status\nreviewed_by\nreviewed_at\nsave()"]
    K --> L["send_decision_email\nper doctor"]
    L --> J

    J -->|"Loop done"| M["Success message\nN updated"]
    M --> N["Redirect /dashboard/"]
```

---

## 9. Email Stub Flow

The email module `email.py` is structured so that wiring real email in the future requires changing only the two private functions `_send_approval_email` and `_send_rejection_email`. The public function `send_decision_email` is called from `review_application` and `bulk_action` — those callers never change. Today both private functions write to the Django logger and print a formatted message to the runserver console. The `logger.info` calls are useful because they appear in log files even in production-like environments, while `print` is convenient during development.

```mermaid
flowchart TD
    A["send_decision_email\ncalled after save"] --> B{"status?"}

    B -->|"approved"| C["_send_approval_email"]
    B -->|"rejected"| D["_send_rejection_email"]
    B -->|"other"| E["Do nothing\nSafe no-op"]

    C --> F["logger.info\nApproval log entry"]
    C --> G["print to console\nTO SUBJECT BODY"]

    D --> H["logger.info\nRejection + reason"]
    D --> I["print to console\nTO SUBJECT BODY\nwith rejection reason"]

    F --> J["TODO\nReplace with\nsend_mail() or\nSendGrid API\nOnly these two\nfunctions change"]
    G --> J
    H --> J
    I --> J
```

---

## 10. All Comments View Flow

The All Comments page gives staff a bird's-eye view of every internal note made across all applications in one table, sorted newest first. It uses `select_related('application', 'author')` so Django fetches all related data in a single SQL JOIN — no extra query per row. Staff can jump directly to any application from this view using the View button on each row.

```mermaid
flowchart TD
    A["Staff clicks\nAll Comments in navbar"] --> B["GET /comments/\nLogin check"]

    B -->|"No session"| BX["Redirect /"]
    B -->|"OK"| C["Comment.objects.all()\nselect_related\napplication + author\norder by created_at DESC"]

    C --> D["Render all_comments.html\nDoctor Name\nStatus badge\nComment preview\nAuthor\nDate\nView button"]

    D --> E{"Staff action"}

    E -->|"Clicks View"| F["GET /application/pk/\nFull detail page\nfull comment thread"]

    E -->|"Scanning activity"| G["Stays on page\nSees all notes\nacross all doctors"]
```

---

## 11. Yellow Comment Dot Logic

The yellow dot signals that an application has at least one internal comment — without opening it. It is computed with a single efficient query returning only IDs, converted to a Python `set` for O(1) lookup, then passed into the template context. The template does `app.pk in commented_ids` per row — no extra DB queries per row, no N+1 problem.

```mermaid
flowchart TD
    A["dashboard view runs"] --> B["Comment.objects\n.values_list application_id\nflat=True .distinct()\nOne DB query"]

    B --> C["Result e.g.\n1 3 7\nConvert to set"]

    C --> D["Pass commented_ids\ninto template context"]

    D --> E["Template loops\neach row"]

    E --> F{"app.pk\nin commented_ids?"}

    F -->|"Yes"| G["Render\nspan.comment-dot\nyellow circle\nnext to name"]

    F -->|"No"| H["No dot\nName alone"]

    G --> I["CSS\n10px yellow circle\nglow ring\ntitle Has comments\ntooltip on hover"]
```

---

## 12. Export CSV Flow

The Export CSV button passes the current `?status=` and `?q=` params into the export URL so the download always matches exactly what is visible on the dashboard. The response uses `content_type=text/csv` and a `Content-Disposition: attachment` header so the browser treats it as a file download rather than a page render. The CSV includes all fields needed for reporting — ID, doctor info, status, rejection reason, reviewer, timestamps.

```mermaid
flowchart TD
    A["Staff clicks Export CSV\nCarries current\n?status=&q= params"] --> B["GET /export/\nSame filter logic\nas dashboard"]

    B --> C["Apply status filter\nApply search filter\nSame queryset\nas screen shows"]

    C --> D["HttpResponse\ncontent_type=text/csv\nContent-Disposition\nattachment filename"]

    D --> E["Write header row\nID Name Email Phone\nSpecialization Status\nRejection Reason\nReviewed By At\nSubmitted At"]

    E --> F["Loop queryset\nOne row per application"]

    F --> G["Write row\nFormatted dates\nUsername or blank\nReadable status"]

    G --> F

    F -->|"Done"| H["Browser receives\nfile stream\nSaves as\napplications.csv"]
```

---

## 13. Complete System Flow — Admin to Final Decision

This is the end-to-end picture of the entire portal. The platform admin controls all access — they create staff accounts via the Django admin panel and share credentials. The staff member logs in, reviews doctor applications, leaves internal comments if needed, and makes the final approve or reject decision. The decision is written to the database with a full record of who decided and when — this is the audit trail the RBAC system relies on.

```mermaid
flowchart TD
    subgraph Admin["Platform Admin — RBAC Layer"]
        AA["Admin logs into /admin/"]
        AB["Creates User account\nusername password\nis_staff=true"]
        AC["Shares credentials\nwith staff member\nNo self-registration"]
    end

    subgraph DataIn["Doctor Application Data"]
        CA["Doctor submits\non other platform"]
        CB["Files stored in\nmedia/doctor_docs/\nLater GCP"]
        CC["DoctorApplication row\ncreated in DB\nstatus=pending"]
    end

    subgraph Staff["Staff Member Work"]
        BA["Staff logs in\nvia /"]
        DA["Sees pending row\non dashboard\nYellow dot if noted"]
        DB["Opens detail page\nReads info\nOpens documents"]
        DC["Adds internal\ncomment if needed"]
        DD{"Decision"}
    end

    subgraph Decision["Decision Recorded"]
        EA["Approve\nstatus=approved\nreviewed_by=user\nreviewed_at=now"]
        EB["Reject\nstatus=rejected\nreason stored\nreviewed_by=user\nreviewed_at=now"]
        EC["Email stub\nconsole log\nReal email later"]
        ED["Dashboard updated\nBadge shows result"]
    end

    AA --> AB --> AC
    CA --> CB --> CC
    AC --> BA
    BA --> DA
    CC --> DA
    DA --> DB --> DC --> DD
    DD -->|"Approve"| EA --> EC --> ED
    DD -->|"Reject"| EB --> EC --> ED
```

---

## 14. Future Integration — What Changes and What Does Not

The code is structured so each of the four major future upgrades requires a change in exactly one place. The rest of the codebase stays untouched.

- **SQLite → PostgreSQL**: change two lines in `settings.py` under `DATABASES`
- **Local folder → GCP**: replace the `os.listdir` block in `application_detail` view with GCP Storage client calls
- **Email stub → Real email**: fill in the two private functions in `email.py`
- **Seed data → Live pull**: replace the seed command with a job that reads from the main Mental Space platform DB or API

```mermaid
flowchart LR
    subgraph Today["Today — Dev"]
        T1["SQLite\ndb.sqlite3"]
        T2["media/ folder\nLocal files"]
        T3["email.py\nConsole print"]
        T4["seed_data.py\nFake rows"]
    end

    subgraph Change["Change Point"]
        C1["settings.py\nDATABASES block"]
        C2["application_detail\nview\nos.listdir block"]
        C3["email.py\n_send_approval\n_send_rejection"]
        C4["New command\nor scheduled job"]
    end

    subgraph Future["Future — Production"]
        F1["PostgreSQL\nCentralized DB"]
        F2["GCP Cloud Storage\nBucket paths"]
        F3["Real Email\nSendGrid etc"]
        F4["Live Doctor Data\nMain platform"]
    end

    T1 -->|"One settings change"| C1 --> F1
    T2 -->|"One view block change"| C2 --> F2
    T3 -->|"Two function bodies"| C3 --> F3
    T4 -->|"Replace command"| C4 --> F4
```

---

## URL Summary Table

| URL | Method | View | Login | What Happens |
|---|---|---|---|---|
| `/` | GET | `home` | No | Shows login form |
| `/` | POST | `home` | No | Authenticates, sets session, redirects to dashboard |
| `/dashboard/` | GET | `dashboard` | Yes | Application list with filter, search, pagination, stat cards, yellow dots |
| `/application/<pk>/` | GET | `application_detail` | Yes | Doctor info, document links, comment thread, approve/reject buttons |
| `/application/<pk>/` | POST | `application_detail` | Yes | Saves new comment, PRG redirect back to GET |
| `/application/<pk>/review/` | POST | `review_application` | Yes | Saves decision, triggers email stub, redirects to dashboard |
| `/bulk-action/` | POST | `bulk_action` | Yes | Processes multiple pending applications, email stub per doctor |
| `/comments/` | GET | `all_comments` | Yes | All comments across all applications newest first |
| `/export/` | GET | `export_csv` | Yes | Streams CSV download matching current filter |
| `/logout/` | GET | `logout_view` | Yes | Clears session, redirects to login |
| `/admin/` | GET/POST | Django Admin | Superuser | Create staff users, inspect all DB records |
| `/media/<path>` | GET | Django static | No | Serves doctor documents from media/ folder |
