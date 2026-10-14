from django.urls import path
from demo.services import redirect_link
urlpatterns=[path("s/<str:code>/",redirect_link)]
