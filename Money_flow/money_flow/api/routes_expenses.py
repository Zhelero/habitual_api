from fastapi import APIRouter, Depends, status
from typing import List

from ..schemas import ExpenseCreate, ExpenseResponse, ExpenseUpdate, TotalResponse
from ..services import ExpenseService
from ..dependencies import get_expense_service

router = APIRouter(prefix="/expenses", tags=["Expenses"])

@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create(
        request: ExpenseCreate,
        service: ExpenseService = Depends(get_expense_service),
):
    expense = service.spend(
            amount=request.amount,
            money_source=request.money_source,
            category=request.category
    )

    return expense

@router.get("/", response_model=List[ExpenseResponse])
def read_expenses(
        category: str | None = None,
        money_source: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
        service: ExpenseService = Depends(get_expense_service),
):
        return service.get_filtered(
            category=category,
            money_source=money_source,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            order=order,
        )


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    deal_id: int,
    service: ExpenseService = Depends(get_expense_service),
):
    service.delete(deal_id)

@router.patch("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_expense(
        deal_id: int,
        payload: ExpenseUpdate,
        service: ExpenseService = Depends(get_expense_service),
):
    service.edit(
        deal_id,
        amount=payload.amount,
        money_source=payload.money_source,
        category=payload.category,
        )

@router.get("/total", response_model=TotalResponse)
def get_total(
    category: str | None = None,
    service: ExpenseService = Depends(get_expense_service),
):
    total = service.total(category)
    return {"total": total}