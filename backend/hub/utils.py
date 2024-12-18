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


def decode_url_token_from_request(request):
    if not hasattr(request.resolver_match, "captured_kwargs"):
        return None
    url_token = request.resolver_match.captured_kwargs.get("url_token")

    return decode_url_token(url_token=url_token)


def decode_url_token(url_token=None):
    if not url_token:
        return None

    try:
        decoded = urlsafe_base64_decode(url_token).decode().split("!!")
    except ValueError:
        return None

    if len(decoded) != 3:
        return None

    try:
        subject_pk = decoded[0]
    except ValueError:
        return None

    return {
        "subject_pk": subject_pk,
        "iso_ts": decoded[1],
        "sig": decoded[2],
    }


def validate_decoded_url_token(decoded_token, max_seconds):

    if decoded_token is None:
        return False

    subject_pk: int = decoded_token.get("subject_pk")
    iso_ts: str = decoded_token.get("iso_ts")
    sig: str = decoded_token.get("sig")

    if not subject_pk or not iso_ts or not sig:
        return False

    try:
        ts = datetime.fromisoformat(iso_ts)
    except ValueError:
        return False

    delta = (timezone.now() - ts).seconds
    if delta > max_seconds:
        return False
    elif delta < 0:
        return False

    # noinspection InsecureHash
    current_sig = hashlib.sha256(f"USER ID={subject_pk} T={iso_ts} K={settings.SECRET_KEY_HASH}".encode()).hexdigest()

    if sig != current_sig:
        return False

    return True


def create_expiring_url_token(subject_pk):
    """
    Create a URL-safe token composed of three parts:
    {subject_id}-{timestamp}-{hash}
    """
    iso_ts = timezone.now().isoformat()

    # noinspection InsecureHash
    sig: str = hashlib.sha256(f"USER ID={subject_pk} T={iso_ts} K={settings.SECRET_KEY_HASH}".encode()).hexdigest()

    unencoded_token = "!!".join([str(subject_pk), iso_ts, sig])

    return urlsafe_base64_encode(unencoded_token.encode())


def expiring_url(max_seconds=settings.EXPIRING_URL_DELTA):
    def decorator(function):
        def wrapper(request, url_token, *args, **kwargs):
            decoded_token = decode_url_token(url_token=url_token)
            if not validate_decoded_url_token(decoded_token, max_seconds):
                raise PermissionDenied()
            return function(request, *args, **kwargs)

        return wrapper

    return decorator
