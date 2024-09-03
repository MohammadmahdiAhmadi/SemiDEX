from django.urls import path
from .views import *

urlpatterns = [
    path('', SwapingView.as_view()),
    path('History/', SwapHistoryView.as_view()),
]
