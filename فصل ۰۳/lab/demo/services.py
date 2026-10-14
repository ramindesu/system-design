from django.db import transaction
from .models import Inventory, Reservation
class NotEnoughStock(Exception): pass
class RequestConflict(Exception): pass

def reserve(item_id, user_id, request_id, quantity):
    if type(quantity) is not int or quantity < 1:
        raise ValueError("quantity must be a positive integer")
    with transaction.atomic(using="default"):
        item = Inventory.objects.using("default").select_for_update().get(pk=item_id)
        old = Reservation.objects.using("default").filter(request_id=request_id).first()
        if old:
            if (old.user_id, old.inventory_id, old.quantity) != (user_id, item_id, quantity):
                raise RequestConflict("request_id reused with different payload")
            return old
        if item.available < quantity:
            raise NotEnoughStock()
        item.available -= quantity
        item.save(using="default", update_fields=["available"])
        return Reservation.objects.using("default").create(user_id=user_id, inventory=item, quantity=quantity, request_id=request_id)
