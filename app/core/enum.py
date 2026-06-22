from enum import Enum


class HabitFilter(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    ALL = "all"
