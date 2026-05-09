"""Complaint creation API."""

from fastapi import APIRouter, File, Form, UploadFile
from uuid import uuid4

router = APIRouter()


@router.post("/create")
async def create_complaint(
    image: UploadFile = File(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form(...),
    userId: str = Form(...),
):
    return {
        "success": True,
        "complaintId": str(uuid4()),
        "filename": image.filename,
        "description": description,
        "latitude": latitude,
        "longitude": longitude,
        "address": address,
        "userId": userId,
        "status": "processing",
    }