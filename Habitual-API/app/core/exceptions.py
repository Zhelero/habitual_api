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

class UserAlreadyExistsError(AppError):
    status_code = 409
    detail = "User already exists"

class PasswordCannotBeEmptyError(AppError):
    status_code = 400
    detail = "Password can not be empty"

class PasswordTooShortError(AppError):
    status_code = 400
    detail = "Password too short"

class InvalidCredentialsError(AppError):
    status_code = 401
    detail = "Invalid credentials"

class UserNotFoundError(AppError):
    status_code = 404
    detail = "User not found"

class InvalidTokenError(AppError):
    status_code = 401
    detail = "Invalid token"

class TokenRevokedError(AppError):
    status_code = 401
    detail = "Token revoked"