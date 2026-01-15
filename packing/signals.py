# from django.db.models.signals import pre_save, post_save
# from django.dispatch import receiver
# from packing.models import Pannes, Packing

# @receiver(pre_save, sender=Pannes)
# def auto_prepare_panne(sender, instance, **kwargs):
    


#     if not instance.slug:
#         instance.slug = instance.generate_slug()

#     instance.duree = instance.calculate_duree()

#     if instance.description:
#         instance.description = instance.description.upper()
#     if instance.solution:
#         instance.solution = instance.solution.upper()
        
# @receiver(post_save, sender=Packing)
# def update_panne_dates(sender, instance, **kwargs): 
#     source = instance.get_source()
#     if source:
#         # Quand un Packing est sauvegardé, mettre à jour les dates des Pannes liées 
#         Pannes.objects.filter(packing=instance).update(source__date=instance.date)
