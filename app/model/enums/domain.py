import enum

class DomainEnum(str, enum.Enum):
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    RETAIL = "retail"
    TECHNOLOGY = "technology"
    TELECOM = "telecom"
