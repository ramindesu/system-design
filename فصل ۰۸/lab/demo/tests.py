from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import ShortLink
from .services import create_link
class ShortenerTests(TestCase):
    def test_mapping_and_redirect(self):
        a=create_link("https://example.com/a"); b=create_link("https://example.com/b")
        self.assertNotEqual(a.code,b.code)
        response=self.client.get(f"/s/{a.code}/")
        self.assertEqual(response.status_code,302)
        self.assertEqual(response["Location"],a.target)
    def test_invalid_target_not_stored(self):
        with self.assertRaises(ValidationError):create_link("javascript:alert(1)")
        self.assertEqual(ShortLink.objects.count(),0)
    def test_missing_code(self):
        self.assertEqual(self.client.get("/s/missing/").status_code,404)
