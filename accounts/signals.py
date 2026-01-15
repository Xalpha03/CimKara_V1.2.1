from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profil, Site

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    if created:
        # Créer un profil automatiquement pour chaque nouvel utilisateur
        # Note: Les champs obligatoires (poste, site) devront être remplis via le formulaire
        pass
    else:
        # Sauvegarder le profil seulement s'il existe déjà
        if hasattr(instance, 'profil'):
            instance.profil.save()
            

