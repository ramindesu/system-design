from django.db import transaction
from django.utils import timezone
from .models import Stock,Order,OrderEvent

def checkout(stock_id,user_id,quantity,request_id):
    if type(quantity) is not int or quantity<1:raise ValueError("invalid quantity")
    with transaction.atomic():
        stock=Stock.objects.select_for_update().get(pk=stock_id)
        previous=Order.objects.filter(request_id=request_id).first()
        if previous:
            if (previous.stock_id,previous.user_id,previous.quantity)!=(stock_id,user_id,quantity):
                raise ValueError("idempotency payload mismatch")
            return previous
        if stock.available<quantity:raise ValueError("not enough stock")
        stock.available-=quantity;stock.save(update_fields=["available"])
        order=Order.objects.create(user_id=user_id,stock=stock,quantity=quantity,request_id=request_id)
        OrderEvent.objects.create(order=order)
        return order

def publish_events(publish):
    events=list(OrderEvent.objects.filter(published_at__isnull=True).order_by("id")[:100])
    for event in events:
        publish(str(event.order_id))
        OrderEvent.objects.filter(pk=event.pk,published_at__isnull=True).update(published_at=timezone.now())
    return len(events)
