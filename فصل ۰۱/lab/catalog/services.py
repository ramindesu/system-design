from decimal import Decimal, InvalidOperation
from django.core.cache import cache
from django.db import transaction
from .models import Book


def book_key(pk):
    return f"book:v1:{pk}"


def serialize_book(book):
    return {"id": book.pk, "title": book.title, "price": str(book.price)}


def get_book(pk, *, fresh=False):
    if fresh:
        return serialize_book(Book.objects.using("default").get(pk=pk))
    missing = object()
    data = cache.get(book_key(pk), missing)
    if data is not missing:
        return data
    # A primary refill prevents replication lag from refilling an invalidated key.
    # Concurrent cache-fill / write races can still exist; this is eventual consistency.
    data = serialize_book(Book.objects.using("default").get(pk=pk))
    cache.set(book_key(pk), data, timeout=30)
    return data


def update_price(pk, raw_price):
    try:
        price = Decimal(str(raw_price))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("price must be a finite nonnegative decimal") from None
    if (not price.is_finite() or price < 0 or price > Decimal("99999999.99")
            or price != price.quantize(Decimal("0.01"))):
        raise ValueError("price must have at most two decimal places and fit the field")
    with transaction.atomic(using="default"):
        book = Book.objects.using("default").select_for_update().get(pk=pk)
        book.price = price
        book.save(using="default", update_fields=["price", "updated_at"])
        transaction.on_commit(lambda: cache.delete(book_key(pk)), using="default")
    return serialize_book(book)
