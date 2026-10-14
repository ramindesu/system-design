from decimal import Decimal
from django.core.management.base import BaseCommand
from catalog.models import Book


class Command(BaseCommand):
    help = "Create one teaching record on the primary."

    def handle(self, *args, **options):
        Book.objects.using("default").update_or_create(pk=1, defaults={"title": "System Design", "price": Decimal("100.00")})
        self.stdout.write("Primary book 1 is ready.")
