from django.urls import path
from catalog import views

urlpatterns = [
    path("", views.home),
    path("books/<int:pk>/", views.book_detail),
    path("books/<int:pk>/price/", views.change_price),
]
