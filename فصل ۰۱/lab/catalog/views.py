import json
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Book
from .services import get_book, update_price


@require_GET
@ensure_csrf_cookie
def home(request):
    return HttpResponse("Django lab: GET /books/1/ ; GET /books/1/?fresh=1 ; tests demonstrate replica lag.")


@require_GET
def book_detail(request, pk):
    try:
        return JsonResponse(get_book(pk, fresh=request.GET.get("fresh") == "1"))
    except Book.DoesNotExist:
        return JsonResponse({"error": "book not found"}, status=404)


@require_POST
@login_required
def change_price(request, pk):
    if not request.user.has_perm("catalog.change_book"):
        return JsonResponse({"error": "permission required"}, status=403)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError("JSON object required")
        data = update_price(pk, payload["price"])
    except (ValueError, KeyError, UnicodeDecodeError):
        return JsonResponse({"error": "valid price is required"}, status=400)
    except Book.DoesNotExist:
        return JsonResponse({"error": "book not found"}, status=404)
    return JsonResponse(data)
