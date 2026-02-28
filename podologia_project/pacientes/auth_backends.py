from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CaseInsensitiveUsernameOrEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        identifier = (username or kwargs.get(user_model.USERNAME_FIELD) or "").strip()

        if not identifier or password is None:
            return None

        user = user_model._default_manager.filter(username__iexact=identifier).first()
        if user is None:
            email_field = getattr(user_model, "EMAIL_FIELD", "email")
            if email_field:
                matches = list(user_model._default_manager.filter(**{f"{email_field}__iexact": identifier})[:2])
                if len(matches) == 1:
                    user = matches[0]

        if user is not None and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
