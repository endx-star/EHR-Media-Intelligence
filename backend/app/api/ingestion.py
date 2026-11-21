from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import MAX_UPLOAD_BYTES
from app.ingestion.cleaner import build_report
from app.ingestion.parsers import InputParseError, parse_file

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.post("/upload")
async def upload_and_clean(file: UploadFile = File(...)):
    """Parse and clean one small synthetic EHR export.

    This MVP does not persist uploaded files. Authentication and authorization
    must be added before exposing the endpoint beyond a trusted local demo.
    """
    filename = file.filename or "upload"
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the configured upload size limit",
            )
        source_format, raw_records = parse_file(filename, content)
        report = build_report(raw_records, source_format)
        return report.model_dump(mode="json")
    except InputParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    finally:
        await file.close()
