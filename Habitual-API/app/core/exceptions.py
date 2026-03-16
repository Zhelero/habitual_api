class AppError(Exception):
    status_code: int = 400
    detail: str = "Application error"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)

class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found"

class BadRequestError(AppError):
    status_code = 400
    detail = "Bad request"

class HabitAlreadyExistsError(AppError):
    status_code = 409
    detail = "Habit already exists"

class HabitAlreadyMarkedError(AppError):
    status_code = 409
    detail = "Habit already marked as done today"

class HabitNotMarkedError(AppError):
    status_code = 409
    detail = "Habit not marked today"

class AtLeastOneFieldError(AppError):
    status_code = 400
    detail = "At least one field is required"

class NameCannotBeEmptyError(AppError):
    status_code = 400
    detail = "Name can not be empty"