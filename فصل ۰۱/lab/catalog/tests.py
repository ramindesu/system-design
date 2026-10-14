from decimal import Decimal
from django.contrib.auth.models import Permission, User
from django.core.cache import cache
from django.db import transaction
from django.test import TestCase, TransactionTestCase, override_settings
from .models import Book
from .routing import primary_reads
from .services import book_key, get_book, update_price


@override_settings(REPLICA_ENABLED=True)
class ReplicaTests(TestCase):
    databases = {"default", "replica"}

    def setUp(self):
        cache.clear()
        Book.objects.using("default").create(pk=1, title="Design", price="120.00")
        Book.objects.using("replica").create(pk=1, title="Design", price="100.00")

    def test_eventual_read_can_be_stale(self):
        # TestCase wraps default in atomic, so route a request outside that condition.
        from unittest.mock import patch
        with patch("catalog.routing.connections") as conns:
            conns["default"].in_atomic_block = False
            self.assertEqual(Book.objects.get(pk=1).price, Decimal("100.00"))

    def test_explicit_read_and_primary_context(self):
        self.assertEqual(Book.objects.using("replica").get(pk=1).price, Decimal("100.00"))
        with primary_reads():
            self.assertEqual(Book.objects.get(pk=1).price, Decimal("120.00"))

    def test_auth_is_primary(self):
        self.assertEqual(User.objects.all().db, "default")

    def test_atomic_reads_are_primary(self):
        with transaction.atomic(using="default"):
            self.assertEqual(Book.objects.all().db, "default")

    def test_write_from_replica_object_goes_to_primary(self):
        book = Book.objects.using("replica").get(pk=1)
        book.price = Decimal("130.00")
        book.save(update_fields=["price"])
        self.assertEqual(Book.objects.using("default").get(pk=1).price, Decimal("130.00"))
        self.assertEqual(Book.objects.using("replica").get(pk=1).price, Decimal("100.00"))

    def test_commit_invalidates_and_cache_refills_from_primary(self):
        cache.set(book_key(1), {"price": "old"})
        with self.captureOnCommitCallbacks(execute=True):
            data = update_price(1, "140.00")
            self.assertEqual(cache.get(book_key(1)), {"price": "old"})
        self.assertEqual(data["price"], "140.00")
        self.assertIsNone(cache.get(book_key(1)))
        self.assertEqual(get_book(1)["price"], "140.00")

    def test_rollback_keeps_cache_and_database(self):
        cache.set(book_key(1), {"price": "120.00"})
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    update_price(1, "140.00")
                    raise RuntimeError("rollback")
            except RuntimeError:
                pass
        self.assertEqual(cache.get(book_key(1)), {"price": "120.00"})
        self.assertEqual(Book.objects.using("default").get(pk=1).price, Decimal("120.00"))

    def test_invalid_prices(self):
        for price in ("NaN", "Infinity", "-1", "1.001", "abc", "100000000.00", None):
            with self.subTest(price=price), self.assertRaises(ValueError):
                update_price(1, price)

    def test_fresh_read_bypasses_stale_cache(self):
        cache.set(book_key(1), {"price": "old"})
        self.assertEqual(get_book(1, fresh=True)["price"], "120.00")

    def test_post_requires_login_and_permission(self):
        response = self.client.post("/books/1/price/", data='{"price":"150"}', content_type="application/json")
        self.assertEqual(response.status_code, 302)
        user = User.objects.create_user("reader", password="test-password")
        self.client.force_login(user)
        self.assertEqual(self.client.post("/books/1/price/", data='{"price":"150"}', content_type="application/json").status_code, 403)
        user.user_permissions.add(Permission.objects.get(codename="change_book"))
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post("/books/1/price/", data='{"price":"150"}', content_type="application/json").status_code, 200)

    def test_bad_json_and_missing_book(self):
        self.assertEqual(self.client.get("/books/999/").status_code, 404)
        user = User.objects.create_superuser("admin", password="test-password", email="")
        self.client.force_login(user)
        for body in ('[]', '{', '{"price":"NaN"}'):
            self.assertEqual(self.client.post("/books/1/price/", data=body, content_type="application/json").status_code, 400)

    def test_csrf_is_required(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        user = User.objects.create_superuser("csrf-admin", password="test-password", email="")
        client.force_login(user)
        self.assertEqual(client.post("/books/1/price/", data='{"price":"150"}', content_type="application/json").status_code, 403)


@override_settings(REPLICA_ENABLED=True)
class AutocommitRoutingTests(TransactionTestCase):
    databases = {"default", "replica"}

    def setUp(self):
        cache.clear()
        Book.objects.using("default").create(pk=1, title="Design", price="120.00")
        Book.objects.using("replica").create(pk=1, title="Design", price="100.00")

    def test_real_query_routing_outside_atomic(self):
        self.assertEqual(Book.objects.get(pk=1).price, Decimal("100.00"))
        with primary_reads():
            self.assertEqual(Book.objects.get(pk=1).price, Decimal("120.00"))
        self.assertEqual(Book.objects.get(pk=1).price, Decimal("100.00"))

    def test_actual_commit_and_cache_query_counts(self):
        cache.set(book_key(1), {"price": "old"})
        update_price(1, "150.00")
        self.assertIsNone(cache.get(book_key(1)))
        with self.assertNumQueries(1, using="default"):
            self.assertEqual(get_book(1)["price"], "150.00")
        with self.assertNumQueries(0, using="default"):
            self.assertEqual(get_book(1)["price"], "150.00")

    def test_lazy_query_evaluates_after_context_exits(self):
        with primary_reads():
            queryset = Book.objects.filter(pk=1)
        self.assertEqual(queryset.get().price, Decimal("100.00"))
        with primary_reads():
            books = list(Book.objects.filter(pk=1))
        self.assertEqual(books[0].price, Decimal("120.00"))
