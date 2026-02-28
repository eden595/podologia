from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase


class CaseInsensitiveLoginTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username="Paola",
            email="Paola.Baeza@example.com",
            password="ClaveSegura123",
        )

    def test_authenticates_with_username_ignoring_case(self):
        user = authenticate(username="paola", password="ClaveSegura123")
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.user.pk)

    def test_authenticates_with_email_ignoring_case(self):
        user = authenticate(username="PAOLA.BAEZA@EXAMPLE.COM", password="ClaveSegura123")
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.user.pk)
