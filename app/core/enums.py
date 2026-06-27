from enum import Enum


class HabitFilter(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    ALL = "all"


class HabitColor(str, Enum):
    SLATE = "slate"
    BLUE = "blue"
    EMERALD = "emerald"
    AMBER = "amber"
    ROSE = "rose"
    VIOLET = "violet"
