# Security Architecture — Adrar AI / JAD2 Advisory

## Authentication & Authorization

- **JWT verification**: HS256 with `aud: "authenticated"` claim required. Generic 401 on failure — no oracle leakage.
- **Tenant isolation**: `bureau_id` from JWT is UUID-validated before injection into DB GUC (`app.bureau_id`). Supabase RLS then enforces row-level isolation across every table.
- **Role allowlist**: `adrar_role` claim must be one of `{admin, consultant, reviewer}`. Arbitrary strings rejected at 401.
- **No cross-bureau traversal**: RLS policies use `current_setting('app.bureau_id')` — a bureau can never read another bureau's rows, regardless of app-level bugs.

## Data Integrity (§0 Invariants)

- **Append-only activity facts**: `proposed → validated` is the only allowed state transition. `validated → proposed` regression is rejected at DB level by trigger.
- **Human-only validation gate**: The `/validate` PATCH endpoint is the only code path that may write `state='validated'`. No automated path exists.
- **No finalize endpoint**: There is no submit/approve/finalize endpoint anywhere in the API.
- **Immutable snapshots**: `report_snapshots` rows are protected by a trigger that rejects all UPDATE and DELETE operations for any role.
- **Deterministic kernel**: `packages/kernel` is pure Python with no network, LLM, or I/O beyond validated fact data. Same inputs always produce the same `state_hash`.

## File Upload Security

- **MIME allowlist**: Server-side allowlist of permitted content types (PDF, XLSX, DOCX, CSV).
- **Magic byte validation**: File content is inspected beyond the client-claimed MIME type — PDFs must start with `%PDF`, Office formats with `PK\x03\x04`.
- **Filename sanitisation**: `os.path.basename()` + regex strip of unsafe characters + 255-char truncation.
- **Size limits**: 50 MB per file; 10 MB for JSON request bodies (multipart exempt).

## Rate Limiting

- Compute endpoint: 10 requests/minute per IP
- Document upload: 20 requests/minute per IP

## Secrets & Encryption

- **Google refresh tokens**: Encrypted at rest with `pgp_sym_encrypt` using `TOKEN_ENCRYPT_KEY`. Never stored in plaintext.
- **Production secret check**: `config.py` raises `RuntimeError` at startup if `SECRET_KEY` or `JWT_SECRET` are weak (< 32 chars) when `ENVIRONMENT=production`.
- **No secrets in query params**: `google_access_token` is sent in the request body, never as a URL query parameter.

## Transport Security

- **CORS**: Restricted to `ALLOWED_ORIGINS` env var (default: localhost only). Explicit allowlist for production deployment.
- **CSP**: Strict Content Security Policy with `frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`. Production removes `unsafe-eval`.
- **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`.

## Data Residency (§0.11)

- Raw documents, activity facts, snapshots, and computation traces **never leave the tenant region**.
- Google Drive export is **opt-in, default OFF**. Only the consultant-reviewed aggregate report is sent — no raw document or fact data.
- Google edits never sync back (one-way export).
- Bureau `region` is immutable after onboarding (enforced by DB trigger).

## Audit Trail

- Every `proposed → validated` transition is logged to `audit_log`.
- Every compute (snapshot insert) is logged.
- Every document extraction completion is logged.
- Logs are append-only — no UPDATE or DELETE on `audit_log`.

## Reporting

To report a security vulnerability, contact security@jad2advisory.com with a description of the issue, steps to reproduce, and the potential impact. Do not open public GitHub issues for security vulnerabilities.
