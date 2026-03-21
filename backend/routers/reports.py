"""
Octant AI — Reports API Router.

Serves compiled PDF reports from the reports output directory.
Provides a listing endpoint and a download endpoint with proper
Content-Type and Content-Disposition headers for browser downloads.
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def list_reports() -> dict:
    """List all generated PDF reports.

    Scans the reports output directory for .pdf files and returns
    their names, sizes, and modification times.

    Returns:
        Dict with a list of report file metadata objects.
    """
    settings = get_settings()
    reports_dir = Path(settings.REPORTS_OUTPUT_PATH)

    if not reports_dir.exists():
        return {"reports": []}

    reports = []
    for pdf_file in sorted(reports_dir.glob("*.pdf")):
        stat = pdf_file.stat()
        reports.append({
            "filename": pdf_file.name,
            "size_bytes": stat.st_size,
            "modified": stat.st_mtime,
            "url": f"/api/reports/{pdf_file.name}",
        })

    logger.info("Listed %d reports", len(reports))
    return {"reports": reports}


@router.get("/{filename}")
async def download_report(filename: str) -> FileResponse:
    """Download a specific PDF report by filename.

    Serves the file with Content-Type: application/pdf and
    Content-Disposition: attachment headers so the browser
    triggers a file download.

    Args:
        filename: The PDF filename to download (e.g., "report_abc123.pdf").

    Returns:
        FileResponse streaming the PDF file.

    Raises:
        HTTPException: If the filename is not found or contains path traversal.
    """
    # Guard against path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    settings = get_settings()
    file_path = Path(settings.REPORTS_OUTPUT_PATH) / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Report '{filename}' not found",
        )

    logger.info("Serving report — filename=%s", filename)

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
