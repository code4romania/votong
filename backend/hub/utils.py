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


def decode_url_token(url_token):
    try:
        decoded = urlsafe_base64_decode(url_token).decode().split("!!")
    except ValueError:
        print("Broken token")
        return False

    if len(decoded) != 3:
        print("Broken token components")
        return False

    try:
        user_pk = int(decoded[0])
    except ValueError:
        return False

    return {
        "user_pk": user_pk,
        "iso_ts": decoded[1],
        "sig": decoded[2],
    }


def validate_expiring_url_token(url_token, max_seconds):

    decoded_token = decode_url_token(url_token)

    if decoded_token is False:
        return decoded_token

    user_pk: int = decoded_token["user_pk"]
    iso_ts: str = decoded_token["iso_ts"]
    sig: str = decoded_token["sig"]

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

    # noinspection InsecureHash
    current_sig = hashlib.sha256(f"USER ID={user_pk} T={iso_ts} K={settings.SECRET_KEY_HASH}".encode()).hexdigest()

    if sig != current_sig:
        print("Signature not valid")
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

    unencoded_token = "!!".join([subject_pk, iso_ts, sig])

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
