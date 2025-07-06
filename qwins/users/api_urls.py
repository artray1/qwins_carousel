from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

# router = DefaultRouter()
# router.register(r"users", UserViewSet)
# router.register(r"promocodes", PromocodeViewSet)

urlpatterns = [
    # path("", include(router.urls)),
    path("login", login),
    path("complete-task", complete_task),
    path("spin", spin_wheel),
]
