from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from catalog.models import Book


class Command(BaseCommand):
    help = "Manually copy catalog rows to the independent SQLite teaching snapshot."

    def handle(self, *args, **options):
        if not settings.SIMULATED_REPLICA:
            raise CommandError("This command must never run against a real replica.")
        rows = list(Book.objects.using("default").values("id", "title", "price", "updated_at"))
        with transaction.atomic(using="replica"):
            Book.objects.using("replica").all().delete()
            Book.objects.using("replica").bulk_create([Book(**row) for row in rows])
        self.stdout.write(f"Copied {len(rows)} catalog rows. Later primary writes will not copy automatically.")
