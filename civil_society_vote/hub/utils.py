from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Template

from hub.models import EmailTemplate


def send_email(template, context, subject, to):
    """
    Sends a single email

    :param template: One of the EMAIL_TEMPLATE_CHOICES from models
    :param context: A dict containing the dynamic values of that template
    :param subject: The subject of the email
    :param to: Destination email address
    :return: Message send result
    """
    tpl = EmailTemplate.objects.get(template=template)

    text_content = Template(tpl.text_content).render(context)
    msg = EmailMultiAlternatives(
        subject, text_content, settings.NO_REPLY_EMAIL, [to], headers={"X-SES-CONFIGURATION-SET": "votong"}
    )

    if tpl.html_content:
        html_content = Template(tpl.html_content).render(context)
        msg.attach_alternative(html_content, "text/html")

    return msg.send()


def build_full_url(request, obj):
    """
    :param request: django Request object
    :param obj: any obj that implements get_absolute_url() and for which
    we can generate a unique URL
    :return: returns the full URL towards the obj detail page (if any)
    """
    return request.build_absolute_uri(obj.get_absolute_url())
