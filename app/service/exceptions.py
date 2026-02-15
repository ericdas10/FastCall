class ServiceError(Exception):
    """Base service-layer error."""

class ValidationError(ServiceError):
    pass

class AlreadyExists(ServiceError):
    pass

class NotFound(ServiceError):
    pass

class NotAllowed(ServiceError):
    pass
