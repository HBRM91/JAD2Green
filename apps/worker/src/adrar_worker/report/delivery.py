"""
Delivery adapters for the generated report.

§0.11 — Two delivery modes:
  1. In-region download (default): returns DOCX bytes. Always available.
  2. Google Docs export (opt-in, default OFF):
       - Requires bureau.google_export_enabled = True
       - Converts DOCX to Google Doc via Drive files.create (convert=True)
       - One-way: Google edits never sync back as source of truth
       - Only the aggregate DOCX crosses the regional boundary — never
         raw activity_facts, documents, or provenance data

Google Docs export is gated at TWO levels:
  1. bureau.google_export_enabled (DB flag, default False) — §0.11
  2. Caller must explicitly pass export=True to google_docs_export()
"""

from __future__ import annotations

import io


class GoogleExportDisabledError(Exception):
    """Raised when Google export is attempted but not enabled for the bureau."""


class GoogleExportNotConfiguredError(Exception):
    """Raised when Google credentials are missing."""


def download_docx(docx_bytes: bytes, filename: str = "bilan_carbone.docx") -> dict:
    """
    Default in-region delivery: return DOCX bytes for HTTP download.
    No data leaves the tenant region.
    """
    return {
        "delivery_method": "download",
        "filename": filename,
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size_bytes": len(docx_bytes),
        "bytes": docx_bytes,
    }


def google_docs_export(
    docx_bytes: bytes,
    bureau_google_export_enabled: bool,
    google_access_token: str | None,
    filename: str = "Bilan Carbone",
) -> dict:
    """
    Export DOCX to Google Docs (opt-in, default OFF — §0.11).

    This function is called ONLY when the consultant explicitly triggers export.
    The DOCX contains aggregate report data only — no raw activity_facts or documents.

    Args:
        docx_bytes: the aggregate DOCX report (renderer output)
        bureau_google_export_enabled: must be True; raises if False
        google_access_token: OAuth2 token for the bureau's Google account
        filename: name for the resulting Google Doc

    Returns:
        {"google_doc_id": ..., "google_doc_url": ..., "delivery_method": "google_docs"}

    Raises:
        GoogleExportDisabledError: if bureau has not opted in
        GoogleExportNotConfiguredError: if no access token
    """
    if not bureau_google_export_enabled:
        raise GoogleExportDisabledError(
            "Google Docs export is disabled for this bureau. "
            "An admin must enable it in bureau settings (§0.11: opt-in, default OFF)."
        )

    if not google_access_token:
        raise GoogleExportNotConfiguredError(
            "No Google OAuth token available. "
            "The bureau must complete the Google Drive authorization flow."
        )

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
    except ImportError as exc:
        raise GoogleExportNotConfiguredError(
            "google-api-python-client not installed. "
            "Install with: pip install google-api-python-client google-auth"
        ) from exc

    creds = Credentials(token=google_access_token)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    media = MediaIoBaseUpload(
        io.BytesIO(docx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        resumable=False,
    )
    file_meta = {
        "name": filename,
        "mimeType": "application/vnd.google-apps.document",  # convert to Google Doc
    }
    # files.create with convert=True (mimeType → Google Doc) — one-way export
    result = service.files().create(
        body=file_meta,
        media_body=media,
        fields="id,webViewLink",
    ).execute()

    return {
        "delivery_method": "google_docs",
        "google_doc_id": result.get("id"),
        "google_doc_url": result.get("webViewLink"),
    }
