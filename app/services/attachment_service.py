# ============================================
# 钢筋精细化管理平台 — 项目附件/效果图服务
# ============================================
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.models.business import ProjectAttachment

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}


def get_attachment_dir(project_id: int) -> str:
    """获取项目附件存储目录"""
    base = os.path.join(current_app.config["UPLOAD_FOLDER"], "attachments", str(project_id))
    os.makedirs(base, exist_ok=True)
    return base


def validate_image(filename: str, mime_type: str = None) -> bool:
    """验证是否为允许的图片类型"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        return False
    return True


def save_attachment(project_id: int, file, description: str = None, created_by: int = None) -> ProjectAttachment:
    """保存上传的附件文件"""
    original_name = secure_filename(file.filename)
    ext = original_name.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    base_dir = get_attachment_dir(project_id)
    file_path = os.path.join(base_dir, unique_name)
    file.save(file_path)

    file_size = os.path.getsize(file_path)

    att = ProjectAttachment(
        project_id=project_id,
        attachment_type="rendering",
        file_name=original_name,
        file_path=os.path.join("attachments", str(project_id), unique_name),
        file_size=file_size,
        mime_type=file.content_type,
        description=description,
        sort_order=0,
        is_cover=False,
        created_by=created_by,
    )
    db.session.add(att)
    db.session.commit()
    return att


def get_project_attachments(project_id: int):
    """获取项目的所有附件（按排序）"""
    return (
        ProjectAttachment.query
        .filter_by(project_id=project_id)
        .order_by(ProjectAttachment.is_cover.desc(), ProjectAttachment.sort_order.asc(), ProjectAttachment.created_at.desc())
        .all()
    )


def get_attachment_by_id(attachment_id: int) -> ProjectAttachment:
    """获取单个附件"""
    return ProjectAttachment.query.get_or_404(attachment_id)


def set_cover(attachment_id: int):
    """设为封面"""
    att = get_attachment_by_id(attachment_id)
    # 先取消该项目所有封面
    ProjectAttachment.query.filter_by(project_id=att.project_id, is_cover=True).update({"is_cover": False})
    att.is_cover = True
    db.session.commit()


def delete_attachment(attachment_id: int):
    """删除附件（包括文件）"""
    att = get_attachment_by_id(attachment_id)
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], att.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
    db.session.delete(att)
    db.session.commit()
