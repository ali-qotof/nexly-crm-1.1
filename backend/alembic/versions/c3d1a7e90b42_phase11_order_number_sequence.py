"""phase11: order_number_seq (atomic order numbers)

Revision ID: c3d1a7e90b42
Revises: 7af3b6985676
"""
from alembic import op

revision = "c3d1a7e90b42"
down_revision = "7af3b6985676"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1")
    # لو وُجدت طلبات سابقة بصيغة ORD-000123 نبدأ بعد أكبر رقم حتى لا يحدث تصادم
    op.execute("""
        SELECT setval('order_number_seq',
          GREATEST(1, COALESCE((SELECT MAX(NULLIF(regexp_replace(order_number, '\\D', '', 'g'), '')::bigint) FROM orders), 0)),
          (SELECT COUNT(*) > 0 FROM orders))
    """)


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS order_number_seq")
