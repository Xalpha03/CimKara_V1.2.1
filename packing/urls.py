from django.urls import path
from .views import *


app_name = 'packing'

urlpatterns = [
    path('', packingHomeView.as_view(), name='packing_home'),
    path('user_packing/<str:username>/', packingUserView.as_view(), name='user_packing'),
    path('user_packing_panne/<str:username>/', packingPanneUserView.as_view(), name='user_packing_panne'),
    path('packing_admin/?download=pdf', packingAdminView.as_view(), name='packing_admin'),
    path('packing_panne_admin/', packingPanneAdminView.as_view(), name='packing_panne_admin'),
    path('ajout_packing', ajout_Packing.as_view(), name='ajout_packing'),
    path('ajout_packing_panne/<slug:slug>/', ajout_Packing_Pannes.as_view(), name='ajout_packing_panne'),
    path('update_packing/<slug:slug>/', update_packing.as_view(), name='update_packing'),
    path('update_packing_panne/<slug:slug>/', update_packing_panne.as_view(), name='update_packing_panne'),
    path('dashboard/', dashboard.as_view(), name='dashboard'),
]