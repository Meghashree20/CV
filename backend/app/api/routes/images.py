'''Authenticated image upload, management, and preprocessing routes.'''

from fastapi import APIRouter, Depends, File, UploadFile, Response

from fastapi.responses import FileResponse

from app.core.dependencies import get_current_user
from app.schemas.image import ImageRead
from app.schemas.image_preprocess import ImagePreprocessResponse
from app.services.image import ImageService
from app.services.image_preprocessing import ImagePreprocessingService

router = APIRouter(prefix="/images", tags=["images"])

image_service = ImageService()

# Upload endpoint
@router.post("/upload", response_model=ImageRead, status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload an image for the authenticated user."""
    return await image_service.upload_image(
        str(current_user["_id"]),
        file,
    )

# Preprocessing endpoint (single definition)
@router.post("/{image_id}/preprocess", response_model=ImagePreprocessResponse)
async def preprocess_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Preprocess an uploaded image without modifying the original file.
    Returns metadata about the preprocessing operation.
    """
    result = await ImagePreprocessingService().preprocess(
        image_id, str(current_user["_id"])
    )
    return result


# List images
@router.get("", response_model=list[ImageRead])
async def list_images(
    current_user: dict = Depends(get_current_user),
):
    """List images belonging to the authenticated user."""
    return await image_service.list_images(str(current_user["_id"]))

# Get image file
@router.get("/{image_id}")
async def get_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve an image belonging to the authenticated user."""
    result = await image_service.get_image(
        image_id,
        str(current_user["_id"]),
    )
    return FileResponse(
        path=result["file_path"],
        media_type=result["content_type"],
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )

# Delete image
@router.delete("/{image_id}", status_code=204)
async def delete_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete an image belonging to the authenticated user."""
    await image_service.delete_image(
        image_id,
        str(current_user["_id"]),
    )
    return Response(status_code=204)
