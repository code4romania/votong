class OrganizationException(Exception):
    pass


class DuplicateOrganizationException(OrganizationException):
    pass


class MissingOrganizationException(OrganizationException):
    pass
