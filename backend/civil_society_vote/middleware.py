from accounts.models import User


def ForceDefaultLanguageMiddleware(get_response):
    def middleware(request):
        if request.META.get("HTTP_ACCEPT_LANGUAGE"):
            del request.META["HTTP_ACCEPT_LANGUAGE"]
        response = get_response(request)
        return response

    return middleware


class CaseInsensitiveUserModel(object):
    def authenticate(self, request, username=None, password=None):
        try:
            user = User.objects.get(email__iexact=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
