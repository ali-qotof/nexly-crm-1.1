from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    مستخدمو النظام: المدير والموظفات (القاعدة 5).

    is_active من SoftDeleteMixin يُستخدم للتعطيل (Disable) وليس فقط للحذف الناعم،
    لأن "تعطيل موظف" و"حذف موظف" كلاهما مطلوب (القاعدة 5 و16) وكلاهما يُترجم لنفس الحقل
    مع تمييز عبر deleted_at (deleted_at = NULL يعني تعطيل عادي، deleted_at != NULL يعني حذف/Soft-delete).
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.EMPLOYEE
    )

    assigned_customers: Mapped[list["CustomerAssignment"]] = relationship(
        back_populates="employee", foreign_keys="CustomerAssignment.employee_id"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username} ({self.role})>"
