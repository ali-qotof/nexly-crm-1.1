"""
سكربت تأسيسي لإنشاء أول حساب SYSTEM_MANAGER.

ضروري لأن واجهة إدارة الموظفين (PHASE 4) نفسها تتطلب مديرًا مُسجَّلًا دخوله أصلًا —
مشكلة "البيضة والدجاجة" الكلاسيكية، تُحل مرة واحدة فقط عبر هذا الأمر، وليس عبر أي مسار API عام
(لا يوجد ولن يوجد endpoint عام لإنشاء مدير بدون مصادقة).

الاستخدام:
    python -m scripts.create_manager --username admin --full-name "مدير النظام"
    (سيُطلب كلمة المرور تفاعليًا بدل تمريرها كـ argument حتى لا تبقى في تاريخ الأوامر)
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.models import User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="إنشاء أول حساب مدير نظام (SYSTEM_MANAGER)")
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()

    password = getpass.getpass("كلمة المرور: ")
    password_confirm = getpass.getpass("تأكيد كلمة المرور: ")
    if password != password_confirm:
        print("كلمتا المرور غير متطابقتين.")
        sys.exit(1)
    if len(password) < 8:
        print("كلمة المرور يجب ألا تقل عن 8 أحرف.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = UserRepository(db).get_by_username(args.username)
        if existing is not None:
            print(f"يوجد بالفعل مستخدم باسم '{args.username}'.")
            sys.exit(1)

        manager = User(
            username=args.username,
            full_name=args.full_name,
            password_hash=hash_password(password),
            role=UserRole.SYSTEM_MANAGER,
        )
        db.add(manager)
        db.commit()
        print(f"تم إنشاء حساب المدير '{args.username}' بنجاح.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
