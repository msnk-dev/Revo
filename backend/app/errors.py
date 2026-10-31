class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class ValidationFailed(Exception):
    def __init__(self, message: str, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}

