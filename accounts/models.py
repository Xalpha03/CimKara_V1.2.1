from django.db import models
from django.contrib.auth.models import User

# Create your models here.
POSTES = [
    ('chefQuart', 'Chef de Quart'),
    ('chefProduction', 'Chef Production'),
    ('operateurBroyage', 'Opérateur Broyage'),
    ('responsablPacking', 'Responsable Packing'),
    ('maintenance', 'Technicien Maintenance'),
    ('administration', 'Administration'),
    ('laborantin', 'Laborantin'),
    # ('broyage', 'Responsable Broyage'),
]

SECTIONS = [
    ('production', 'Production'),
    ('broyage', 'Broyage'),
    ('packing', 'Packing'),
    ('maintenance', 'Maintenance'),
    ('laboratoire', 'Laboratoire'),
    ('administration', 'Administration'),
]


class  Site(models.Model):
    site = models.CharField(max_length=20)
    
    def __str__(self):
        return self.site
        
class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profil")
    section = models.CharField(max_length=50, choices=SECTIONS, blank=True, null=True)
    poste = models.CharField(max_length=100, choices=POSTES)
    role = models.CharField(max_length=50, choices=[('admin', 'Admin'), ('opérateur', 'Opérateur')], default='opérateur')
    site = models.ForeignKey(Site, on_delete=models.CASCADE,)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    date_naissance = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Profil de {self.user.username}"



