from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class PasswordDifferentFromPrevious:
    def validate(self, password, user=None):
        if not user:
            return

        # If the newly provided password is in fact still the old password
        # consider it invalid
        if check_password(password, user.password):
            raise ValidationError(
                _("Your new password must be different."),
            )

    def get_help_text(self):
        return _("Please correct the error below. Your new password must be different. Please try again.")
