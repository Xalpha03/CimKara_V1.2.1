from django.contrib import admin
from .models import Post, Packing, Pannes

# Register your models here.
class Post_Admin(admin.ModelAdmin):
    list_display = ('post', 'start_post', 'end_post', 'duree_post')
    fields = ('post', 'start_post', 'end_post')
    search_fields = ('post',)
    list_filter = ('post',) 


class Packing_Admin(admin.ModelAdmin):
    list_display = ('title', 'post', 'site', 'date', 'livraison', 'casse', 'vrack', 'slug')
    fields = ('user', 'post', 'site', 'date', 'livraison', 'casse', 'vrack',)
    search_fields = ('title', 'site__name', 'post__post')
    list_filter = ('site', 'post', 'date')
    
class Pannes_Admin(admin.ModelAdmin):
    def make_title(self, obj): 
        if obj.broyage: 
            return obj.broyage.make_title 
        if obj.packing: 
            return obj.packing.title 
        return "—"
    list_display = ('make_title', 'departement', 'start_panne', 'end_panne', 'duree', 'description', 'solution', 'slug')
    fields = ('broyage', 'packing', 'production', 'departement', 'start_panne', 'end_panne', 'description', 'solution')
    
    ordering = ('-packing__date', '-broyage__date')
    search_fields = ('broyage__make_title', 'packing__title')
    # list_filter = ('site', 'section', 'date')
    

 
admin.site.register(Post, Post_Admin)
admin.site.register(Pannes, Pannes_Admin)  
admin.site.register(Packing, Packing_Admin)
