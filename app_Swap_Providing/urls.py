from django.urls import path
from .views import *

urlpatterns = [
    path('', ProvidingView.as_view()),
    path('History/', ProviderHistoryView.as_view()),
]
