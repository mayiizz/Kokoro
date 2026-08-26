from fastapi import UploadFile

async def read_syllabus(file: UploadFile = None, text: str = None) -> str:
    """
    Reads syllabus from a file (PDF/Image) or text input.
    For now, this is a placeholder that prefers text if available,
    or returns a dummy string if a file is provided but no text.
    In a real implementation, this would use OCR or PDF parsing.
    """
    if text:
        return text
    
    if file:
        # TODO: Implement OCR / PDF text extraction here
        return f"Content extracted from file: {file.filename}"
    
    return ""
