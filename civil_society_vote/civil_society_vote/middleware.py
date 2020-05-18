def ForceDefaultLanguageMiddleware(get_response):
    def middleware(request):
        if request.META.get("HTTP_ACCEPT_LANGUAGE"):
            del request.META["HTTP_ACCEPT_LANGUAGE"]
        response = get_response(request)
        return response

    return middleware
