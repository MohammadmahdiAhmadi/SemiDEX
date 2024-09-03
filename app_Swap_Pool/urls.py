from django.urls import path
from .views import *

urlpatterns = [
    path('Home/', HomeView.as_view()),
    path('Detail/', PoolsDetailView.as_view()),
    path('UserActivePools/', UserActivePoolsView.as_view()),
    path('Currencies/', CurrenciesView.as_view()),
]
