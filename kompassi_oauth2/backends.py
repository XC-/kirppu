from django.contrib.auth import get_user_model
from django.conf import settings
from requests_oauthlib import OAuth2Session

User = get_user_model()


def user_defaults_from_kompassi(kompassi_user):
    return dict((django_key, kompassi_user[kompassi_key]) for (django_key, kompassi_key) in
                settings.KOMPASSI_USER_MAP_V2)


class KompassiOAuth2AuthenticationBackend(object):
    def authenticate(self, request=None, oauth2_session=None, **kwargs):
        if isinstance(request, OAuth2Session):
            # Django <1.11 compatibility.
            oauth2_session = request
        if oauth2_session is None:
            # Not ours (password login)
            return None

        response = oauth2_session.get(settings.KOMPASSI_API_V2_USER_INFO_URL)
        response.raise_for_status()
        kompassi_user = response.json()

        user, created = User.objects.get_or_create(
            username=kompassi_user['username'],
            defaults=user_defaults_from_kompassi(kompassi_user)
        )

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesDotExist:
            return None
