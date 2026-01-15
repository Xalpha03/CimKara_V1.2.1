from django.urls import path
from.views import *
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.conf.urls.static import static


app_name = 'account'
urlpatterns = [
    path('register/', UserCreate.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', custom_logout, name='logout'),
    path("accueil/<int:pk>/", AccueilView.as_view(), name="accueil"),
    path("auto-login/", auto_login, name="auto-login"),

]
