class OrganizationException(Exception):
    """Some kind of problem with an organization"""



class ClosedRegistrationException(OrganizationException):
    """New organizations cannot be registered anymore"""



class DisabledOrganizationException(OrganizationException):
    """The requested organization has been disabled from the platform"""



class DuplicateOrganizationException(OrganizationException):
    """An organization with the same NGO Hub ID already exists"""



class MissingOrganizationException(OrganizationException):
    """The requested organization does not exist"""



class NGOHubHTTPException(OrganizationException):
    """NGO Hub API error"""

