class OrganizationException(Exception):
    """Some kind of problem with an organization"""

    pass


class ClosedRegistrationException(OrganizationException):
    """New organizations cannot be registered anymore"""

    pass


class DisabledOrganizationException(OrganizationException):
    """The requested organization has been disabled from the platform"""

    pass


class DuplicateOrganizationException(OrganizationException):
    """An organization with the same NGO Hub ID already exists"""

    pass


class MissingOrganizationException(OrganizationException):
    """The requested organization does not exist"""

    pass


class OrganizationRetrievalHTTPException(OrganizationException):
    """The requested organization could not be retrieved from NGO Hub"""

    pass
