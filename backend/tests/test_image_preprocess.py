'''Tests for the image preprocessing endpoint (Phase 5).'''

import hashlib
from pathlib import Path
import asyncio

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.main import create_app
from app.services.image import ImageService
from app.api.routes.images import image_service

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def hash_file(path: Path) -> str:
    """Return SHA256 hash of a file's contents."""
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def create_image(path: Path, fmt: str, size=(100, 200), color=(255, 0, 0), exif_orientation: int | None = None) -> None:
    """Create a simple image file.

    Parameters
    ----------
    path: Path
        Destination file.
    fmt: str
        One of "JPEG", "PNG", "WEBP", "BMP".
    size: tuple[int, int]
        (width, height).
    color: tuple[int, int, int]
        RGB background colour.
    exif_orientation: int | None
        EXIF orientation tag (1‑8) to embed, if any.
    """
    img = Image.new('RGB', size, color)
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[274] = exif_orientation  # 274 = Orientation tag
        img.save(path, fmt, exif=exif)
    else:
        img.save(path, fmt)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def client() -> TestClient:
    """FastAPI test client built from the application factory."""
    app = create_app()
    return TestClient(app)

class FakeImageRepository:
    """In‑memory image repository for tests."""

    def __init__(self):
        self.images = []

    async def create_image(self, user_id, filename, content_type, size_bytes, width, height, uploaded_at):
        from uuid import uuid4
        document = {
            "_id": str(uuid4()),
            "user_id": user_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "width": width,
            "height": height,
            "uploaded_at": uploaded_at,
        }
        self.images.append(document)
        return document

    async def list_by_user(self, user_id, limit=100):
        return [item for item in self.images if item["user_id"] == user_id][:limit]

    async def get_by_id(self, image_id, user_id):
        for item in self.images:
            if item["_id"] == image_id and item["user_id"] == user_id:
                return item
        return None

    async def delete_by_id(self, image_id, user_id):
        for item in self.images:
            if item["_id"] == image_id and item["user_id"] == user_id:
                self.images.remove(item)
                return True
        return False

@pytest.fixture
def image_preprocess_setup(client: TestClient, monkeypatch, tmp_path: Path):
    """Configure fake storage, repository and authentication for preprocessing tests."""
    repo = FakeImageRepository()
    # Patch the image_service used by routes
    monkeypatch.setattr(image_service, "repo", repo)
    monkeypatch.setattr(image_service.settings, "image_storage_path", tmp_path)
    # Patch ImageService.__init__ so new instances use the fake repo and temp storage
    def fake_init(self):
        self.repo = repo
        self.settings = get_settings()
        self.settings.image_storage_path = tmp_path
    monkeypatch.setattr(ImageService, "__init__", fake_init, raising=False)
    test_user = {"_id": "testuserid1", "email": "test1@example.com", "name": "Test User"}
    previous_overrides = dict(client.app.dependency_overrides)
    client.app.dependency_overrides[get_current_user] = lambda: test_user
    yield repo, test_user, tmp_path
    client.app.dependency_overrides.clear()
    client.app.dependency_overrides.update(previous_overrides)

def _mime_for_suffix(suffix: str) -> str:
    mapping = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}
    return mapping.get(suffix.lower(), 'application/octet-stream')

def _upload_image(client: TestClient, path: Path) -> str:
    with path.open('rb') as f:
        files = {'file': (path.name, f, _mime_for_suffix(path.suffix))}
        resp = client.post('/images/upload', files=files)
    assert resp.status_code == 201
    return resp.json()['id']

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_successful_preprocess_jpeg(client: TestClient, image_preprocess_setup, tmp_path: Path):
    repo, user, _ = image_preprocess_setup
    img_path = tmp_path / 'test.jpg'
    create_image(img_path, 'JPEG')
    original_hash = hash_file(img_path)
    image_id = _upload_image(client, img_path)
    resp = client.post(f'/images/{image_id}/preprocess')
    assert resp.status_code == 200
    data = resp.json()
    assert data['image_id'] == image_id
    assert data['original_width'] == 100
    assert data['original_height'] == 200
    assert data['processed_width'] == 100
    assert data['processed_height'] == 200
    assert data['color_mode'] == 'RGB'
    assert data['format'] == 'JPEG'
    assert hash_file(img_path) == original_hash

def test_successful_preprocess_png(client: TestClient, image_preprocess_setup, tmp_path: Path):
    repo, user, _ = image_preprocess_setup
    img_path = tmp_path / 'test.png'
    create_image(img_path, 'PNG')
    image_id = _upload_image(client, img_path)
    resp = client.post(f'/images/{image_id}/preprocess')
    assert resp.status_code == 200
    data = resp.json()
    assert data['original_width'] == 100
    assert data['original_height'] == 200
    assert data['format'] == 'PNG'

def test_successful_preprocess_webp(client: TestClient, image_preprocess_setup, tmp_path: Path):
    repo, user, _ = image_preprocess_setup
    img_path = tmp_path / 'test.webp'
    create_image(img_path, 'WEBP')
    image_id = _upload_image(client, img_path)
    resp = client.post(f'/images/{image_id}/preprocess')
    assert resp.status_code == 200
    data = resp.json()
    assert data['format'] == 'WEBP'

def test_exif_orientation_correction(client: TestClient, image_preprocess_setup, tmp_path: Path):
    repo, user, _ = image_preprocess_setup
    img_path = tmp_path / 'exif.jpg'
    create_image(img_path, 'JPEG', size=(100, 200), exif_orientation=6)
    image_id = _upload_image(client, img_path)
    resp = client.post(f'/images/{image_id}/preprocess')
    assert resp.status_code == 200
    data = resp.json()
    assert data['processed_width'] == 200
    assert data['processed_height'] == 100

def test_resize_to_max_dimension(client: TestClient, image_preprocess_setup, tmp_path: Path):
    repo, user, _ = image_preprocess_setup
    img_path = tmp_path / 'large.jpg'
    create_image(img_path, 'JPEG', size=(3000, 2000))
    image_id = _upload_image(client, img_path)
    resp = client.post(f'/images/{image_id}/preprocess')
    assert resp.status_code == 200
    data = resp.json()
    assert max(data['processed_width'], data['processed_height']) == get_settings().max_image_dimension_px

def test_missing_image_id(client: TestClient, image_preprocess_setup):
    repo, user, _ = image_preprocess_setup
    resp = client.post('/images/invalidid/preprocess')
    assert resp.status_code == 404

def test_cross_user_access(client: TestClient, image_preprocess_setup, tmp_path: Path):
    repo, user, _ = image_preprocess_setup
    img_path = tmp_path / 'user_a.jpg'
    create_image(img_path, 'JPEG')
    image_id = _upload_image(client, img_path)
    other_user = {"_id": "otheruserid", "email": "other@example.com", "name": "Other User"}
    client.app.dependency_overrides[get_current_user] = lambda: other_user
    resp = client.post(f'/images/{image_id}/preprocess')
    assert resp.status_code == 404
    client.app.dependency_overrides[get_current_user] = lambda: user

def test_missing_physical_file(client: TestClient, image_preprocess_setup, tmp_path: Path):
    repo, user, storage_dir = image_preprocess_setup
    img_path = tmp_path / 'todelete.jpg'
    create_image(img_path, 'JPEG')
    image_id = _upload_image(client, img_path)
    stored_doc = next(item for item in repo.images if item['_id'] == image_id)
    stored_file = storage_dir / stored_doc['filename']
    stored_file.unlink()
    resp = client.post(f'/images/{image_id}/preprocess')
    assert resp.status_code == 404

def test_corrupted_image_file(client: TestClient, image_preprocess_setup, tmp_path: Path):
    repo, user, storage_dir = image_preprocess_setup
    img_path = tmp_path / 'valid.jpg'
    create_image(img_path, 'JPEG')
    image_id = _upload_image(client, img_path)
    stored_doc = next(item for item in repo.images if item['_id'] == image_id)
    stored_file = storage_dir / stored_doc['filename']
    with stored_file.open('wb') as f:
        f.write(b'not an image')
    resp = client.post(f'/images/{image_id}/preprocess')
    assert resp.status_code == 400

def test_unsupported_image_format_upload(client: TestClient, image_preprocess_setup, tmp_path: Path):
    img_path = tmp_path / 'bad.bmp'
    create_image(img_path, 'BMP')
    with img_path.open('rb') as f:
        files = {'file': ('bad.bmp', f, 'image/bmp')}
        resp = client.post('/images/upload', files=files)
    assert resp.status_code == 415

def test_unauthenticated_preprocess(client: TestClient, image_preprocess_setup, tmp_path: Path):
    repo, user, _ = image_preprocess_setup
    img_path = tmp_path / 'noauth.jpg'
    create_image(img_path, 'JPEG')
    image_id = _upload_image(client, img_path)
    client.app.dependency_overrides.pop(get_current_user, None)
    resp = client.post(f'/images/{image_id}/preprocess')
    assert resp.status_code == 401
    client.app.dependency_overrides[get_current_user] = lambda: user

# ---------------------------------------------------------------------------
# Direct service test
# ---------------------------------------------------------------------------

def test_service_direct(monkeypatch, tmp_path: Path):
    img_path = tmp_path / 'direct.jpg'
    create_image(img_path, 'JPEG')
    async def fake_get_image(image_id: str, user_id: str):
        return {
            'document': {},
            'file_path': img_path,
            'content_type': 'image/jpeg',
        }
    monkeypatch.setattr(ImageService, 'get_image', staticmethod(fake_get_image))
    from app.services.image_preprocessing import ImagePreprocessingService
    service = ImagePreprocessingService()
    result = asyncio.run(service.preprocess('any', 'user'))
    assert result['original_width'] == 100
    assert result['original_height'] == 200
    assert result['processed_width'] == 100
    assert result['processed_height'] == 200
    assert result['color_mode'] == 'RGB'
    assert result['format'] == 'JPEG'
