
from django.urls import path
from .views import *  

app_name = 'broyage'
urlpatterns = [
    path('', broyageHomeView.as_view(), name='broyage_home'),
    path('user_broyage/<str:username>', broyageUserView.as_view(), name='user_broyage'),
    path('user_broyage_pannes/<str:username>', broyagePanneUser.as_view(), name='user_broyage_panne'),
    path('broyage_admin/', broyageAdmin.as_view(), name='broyage_admin'),
    path('broyage_pannes_admin/', broyagePanneAdmin.as_view(), name='broyage_pannes_admin'),
    path('ajout_totaliseur_1/', ajoutTotaliseur_1.as_view(), name='ajout_totali_1'),
    path('ajout_totaliseur_2/<slug:slug>', ajoutTotaliseur_2.as_view(), name='ajout_totali_2'),
    path('ajout_panne/<slug:slug>/', ajoutBroyagePannes.as_view(), name='ajout_panne'),
    path('update_totaliseur_1/<slug:slug>/', updateTotaliseur_1.as_view(), name='update_totali_1'),
    path('update_totali_2/<slug:slug>/', updateTotaliseur_2.as_view(), name='update_totali_2'),
    path('update_panne/<slug:slug>/', updatePanne.as_view(), name='update_panne'),
    path('dashboard/', dashboard.as_view(), name='dashboard'),
    
    path('user_production/<str:username>', productionUserView.as_view(), name='user_production'),
    path('user_production_pannes/<str:username>', productionUserPanne.as_view(), name='user_production_panne'),
    
]
