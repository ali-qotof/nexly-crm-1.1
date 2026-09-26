import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import StatusConfiguration
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerListItem, PaginatedCustomers


class CustomerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CustomerRepository(db)

    def _status_label_map(self) -> dict[str, str]:
        stmt = select(StatusConfiguration.code, StatusConfiguration.label_ar)
        return dict(self.db.execute(stmt).all())

    def list_customers(
        self,
        *,
        q: str | None = None,
        employee_id: uuid.UUID | None = None,
        unassigned_only: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedCustomers:
        rows, total = self.repo.search(
            q=q,
            employee_id=employee_id,
            unassigned_only=unassigned_only,
            page=page,
            page_size=page_size,
        )
        labels = self._status_label_map()

        items = []
        for (
            customer,
            emp_id,
            emp_name,
            latest_interaction_at,
            latest_status_code,
            latest_order_at,
            latest_order_total,
        ) in rows:
            items.append(
                CustomerListItem(
                    **{
                        k: getattr(customer, k)
                        for k in [
                            "id",
                            "customer_code",
                            "source_customer_id",
                            "name",
                            "phone",
                            "whatsapp",
                            "address",
                            "governorate",
                            "is_active",
                            "created_at",
                        ]
                    },
                    assigned_employee_id=emp_id,
                    assigned_employee_name=emp_name,
                    latest_status_code=latest_status_code,
                    latest_status_label=labels.get(latest_status_code) if latest_status_code else None,
                    latest_interaction_at=latest_interaction_at,
                    latest_order_at=latest_order_at,
                    latest_order_total=float(latest_order_total) if latest_order_total is not None else None,
                )
            )

        return PaginatedCustomers(items=items, total=total, page=page, page_size=page_size)
