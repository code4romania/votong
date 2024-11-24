import hashlib
from datetime import datetime

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode


def build_full_url(request, obj):
    """
    :param request: django Request object
    :param obj: any obj that implements get_absolute_url() and for which
    we can generate a unique URL
    :return: returns the full URL towards the obj detail page (if any)
    """
    return request.build_absolute_uri(obj.get_absolute_url())


def validate_expiring_url_token(url_token, max_seconds):

    try:
        decoded = urlsafe_base64_decode(url_token).decode().split("!!")
    except ValueError:
        print("Broken token")
        return False

    if len(decoded) != 3:
        print("Broken token components")
        return False

    subject_pk = decoded[0]
    iso_ts = decoded[1]
    sig = decoded[2]

    try:
        ts = datetime.fromisoformat(iso_ts)
    except ValueError:
        print("DATE VALUE ERROR")
        return False

    delta = (timezone.now() - ts).seconds
    if delta > max_seconds:
        print("Expired")
        return False
    elif delta < 0:
        print("You cannot have a link created in the future")
        return False

    current_sig = hashlib.sha256(f"USER ID={subject_pk} T={iso_ts} K={settings.SECRET_KEY_HASH}".encode()).hexdigest()
    if sig != current_sig:
        print("Signature not valid")
        return False

    return True


def create_expiring_url_token(subject_pk):
    """
    Create an URL safe token composed of three parts:
    {subject_id}-{timestamp}-{hash}
    """
    iso_ts = timezone.now().isoformat()
    sig: str = hashlib.sha256(f"USER ID={subject_pk} T={iso_ts} K={settings.SECRET_KEY_HASH}".encode()).hexdigest()

    unencoded_token = f"{subject_pk}!!{iso_ts}!!{sig}"
    return urlsafe_base64_encode(unencoded_token.encode())


def hashed_expiring_url(request):
    """
    Validate the `id`, `ts`, and `sign` from an URL GET parameters
    """
    pass


def expiring_url(max_seconds=settings.EXPIRING_URL_DELTA):
    def decorator(function):
        def wrapper(request, url_token, *args, **kwargs):
            if not validate_expiring_url_token(url_token, max_seconds):
                raise PermissionDenied()
            return function(request, *args, **kwargs)

        return wrapper

    return decorator
