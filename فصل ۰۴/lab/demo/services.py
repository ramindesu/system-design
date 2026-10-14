from django.http import JsonResponse
from .algorithms import TokenBucket

def rate_limit_response(bucket):
    allowed, delay = bucket.take()
    if allowed:
        return None
    response = JsonResponse({"error": "too many requests"}, status=429)
    response["Retry-After"] = str(max(1, delay))
    return response
