from django import forms
from django_crispy_bulma.widgets import EmailInput

from hub import models
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV3


class NGOForm(forms.ModelForm):
    class Meta:
        model = models.NGO
        fields = "__all__"


class NGORegisterRequestForm(forms.ModelForm):
    captcha = ReCaptchaField(
        widget=ReCaptchaV3(attrs={"required_score": 0.3, "action": "register"}),
        label="",
    )

    class Meta:
        model = models.RegisterNGORequest
        fields = [
            "name",
            "county",
            "city",
            "address",
            "email",
            "contact_name",
            "contact_phone",
            "social_link",
            "description",
            "past_actions",
            "resource_types",
            "logo",
            "last_balance_sheet",
            "statute",
        ]
        widgets = {
            "email": EmailInput(),
            # "logo": AdminResubmitImageWidget,
            # "last_balance_sheet": AdminResubmitFileWidget,
            # "statute": AdminResubmitFileWidget,
        }


class RegisterNGORequestVoteForm(forms.ModelForm):
    class Meta:
        model = models.RegisterNGORequestVote
        fields = ("vote", "motivation")
