from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.responses import ResumeGenerationRequest, ResumeGenerationResponse
from app.services.resume_service import generate_resume_content
from app.utils.pdf_generator import generate_pdf

router = APIRouter( tags=["Resume"])


# ===============================
# Generate Resume Text Endpoint
# ===============================
@router.post("/generate", response_model=ResumeGenerationResponse)
async def generate_resume_endpoint(request: ResumeGenerationRequest):
    try:
        return await generate_resume_content(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===============================
# Download Resume PDF Endpoint
# ===============================
@router.post("/download-pdf")
async def download_resume_pdf(request: ResumeGenerationRequest):
   
        result = await generate_resume_content(request)

        filepath = generate_pdf(result.ats_optimized_resume_text)

        return FileResponse(
            filepath,
            media_type="application/pdf",
            filename="resume.pdf"
        )

   