"""
تخزين ملفات مرفوعة (صور الشكاوى، إلخ) — تنفيذ محلي بسيط لهذه المرحلة من التطوير.

قيد صريح: هذا يخزّن على القرص المحلي للسيرفر. في الإنتاج الفعلي (PHASE 13) يجب استبداله بتخزين
سحابي (Supabase Storage أو S3-compatible) حتى يعمل بشكل صحيح خلف أكثر من Instance/Worker ولا
يُفقد عند إعادة نشر الحاوية. الواجهة (save_upload → ترجع URL) مصممة بحيث الاستبدال لا يغيّر أي
كود آخر يستدعيها.
"""
import uuid
from pathlib import Path

UPLOAD_DIR = Path("/mnt/user-data/nexly-uploads")
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


class FileStorageError(Exception):
    pass


def save_upload(content: bytes, original_filename: str) -> tuple[str, str]:
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileStorageError(f"نوع الملف '{ext}' غير مسموح")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise FileStorageError("حجم الملف يتجاوز الحد المسموح (10MB)")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{ext}"
    (UPLOAD_DIR / stored_name).write_bytes(content)

    file_url = f"/uploads/{stored_name}"
    return file_url, stored_name
