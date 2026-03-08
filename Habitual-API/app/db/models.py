from datetime import datetime, date

from sqlalchemy import String, Date, ForeignKey, UniqueConstraint, Index, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base

class Habit(Base):
    __tablename__ = 'habits'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    logs: Mapped[list["HabitLog"]] = relationship(
        back_populates="habit",
        cascade="all, delete-orphan"
    )


class HabitLog(Base):
    __tablename__ = 'habit_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    habit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('habits.id', ondelete="CASCADE"),
        index=True
    )

    date: Mapped[date] = mapped_column(Date, nullable=False)

    habit: Mapped["Habit"] = relationship(back_populates="logs")

    __table_args__ = (
        UniqueConstraint("habit_id", "date", name="uq_habit_date"),
        Index("ix_habit_date", "habit_id", "date")
    )