from django.contrib import admin
from .models import Production, Totaliseur_1, Totaliseur_2
# Register your models here.

class Totaliseur_1_Admin(admin.ModelAdmin):
    list_display = ('title', 'post', 'site', 'date', 'compt_totaliseur_1', 'clinker_totaliseur_1', 'gypse_totaliseur_1', 'dolomite_totaliseur_1', 'slug')
    fields = ('user', 'post', 'site', 'date', 'compt_totaliseur_1', 'clinker_totaliseur_1', 'gypse_totaliseur_1', 'dolomite_totaliseur_1')
    search_fields = ('title', 'site__name', 'post__post')
    list_filter = ('site', 'post', 'date')
    
class Totaliseur_2_Admin(admin.ModelAdmin):
    list_display = (
        'title', 'compt_totaliseur_2', 'clinker_totaliseur_2', 'gypse_totaliseur_2', 'dolomite_totaliseur_2',
        'totaliseur__date', 'slug', 'silo_1', 'silo_1_value',
    )
    fields = (
        'totaliseur', 'compt_totaliseur_2', 'clinker_totaliseur_2', 'gypse_totaliseur_2', 'dolomite_totaliseur_2',
        'silo_1', 'silo_2',
    )
    search_fields = ('totaliseur__title', 'totaliseur__site__name', 'totaliseur__post__post')
    list_filter = ('totaliseur__site', 'totaliseur__post', 'totaliseur__date')
    
    
class Production_Admin(admin.ModelAdmin):
    list_display = ('title', 'post', 'site', 'date', 'production', 'conso', 'consignes', 'slug')
    fields = ('user', 'post', 'site', 'date', 'production', 'conso', 'consignes')
    search_fields = ('title', 'site__name', 'post__post')
    list_filter = ('site', 'post', 'date')

admin.site.register(Production, Production_Admin)
admin.site.register(Totaliseur_1, Totaliseur_1_Admin)
admin.site.register(Totaliseur_2, Totaliseur_2_Admin)

