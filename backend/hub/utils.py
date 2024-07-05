def build_full_url(request, obj):
    """
    :param request: django Request object
    :param obj: any obj that implements get_absolute_url() and for which
    we can generate a unique URL
    :return: returns the full URL towards the obj detail page (if any)
    """
    return request.build_absolute_uri(obj.get_absolute_url())
