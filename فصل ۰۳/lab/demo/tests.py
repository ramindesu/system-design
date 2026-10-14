import uuid
from django.contrib.auth.models import User
from django.test import TestCase
from .models import Inventory, Reservation
from .services import reserve, NotEnoughStock, RequestConflict
class ReservationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("reader")
        self.item = Inventory.objects.create(available=2)
        self.key = uuid.uuid4()
    def test_retry_does_not_decrement_twice(self):
        first = reserve(self.item.pk, self.user.pk, self.key, 1)
        again = reserve(self.item.pk, self.user.pk, self.key, 1)
        self.assertEqual(first.pk, again.pk)
        self.item.refresh_from_db()
        self.assertEqual(self.item.available, 1)
    def test_conflicting_replay_is_rejected(self):
        reserve(self.item.pk, self.user.pk, self.key, 1)
        with self.assertRaises(RequestConflict): reserve(self.item.pk, self.user.pk, self.key, 2)
    def test_shortage_has_no_side_effect(self):
        with self.assertRaises(NotEnoughStock): reserve(self.item.pk, self.user.pk, self.key, 3)
        self.item.refresh_from_db()
        self.assertEqual(self.item.available, 2)
        self.assertEqual(Reservation.objects.count(), 0)
    def test_invalid_quantity(self):
        for n in (0,-1,True,1.5):
            with self.assertRaises(ValueError): reserve(self.item.pk, self.user.pk, self.key, n)
