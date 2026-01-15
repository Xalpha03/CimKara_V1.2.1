from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Profil, Site

@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'poste', 'role', 'site', 'section', 'avatar', 'date_naissance')
    search_fields = ('user__username', 'poste')
    list_filter = ('poste', 'site')



class SiteAdmin(admin.ModelAdmin):
    list_display = ['site']
    
admin.site.register(Site, SiteAdmin)