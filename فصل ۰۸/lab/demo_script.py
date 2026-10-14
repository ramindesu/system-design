import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.test import RequestFactory
from demo.services import create_link,redirect_link
link=create_link("https://example.com/articles/system-design")
response=redirect_link(RequestFactory().get("/"),link.code)
print("short path:",f"/s/{link.code}/","status:",response.status_code,"target:",response["Location"])
print("No network request to the target was made.")
