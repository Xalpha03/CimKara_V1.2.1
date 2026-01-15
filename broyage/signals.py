from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Totaliseur_1, Totaliseur_2

@receiver(post_save, sender=Totaliseur_1)
def update_related_totaliseur2(sender, instance, **kwargs):
    # instance = Totaliseur_1 modifié
    t1 = instance

    # récupérer tous les Totaliseur_2 liés
    t2_list = Totaliseur_2.objects.filter(totaliseur=t1)

    for t2 in t2_list:
        # recalculer les champs dépendants
        t2.dif_clinker = t2.clinker_totaliseur_2 - t1.clinker_totaliseur_1
        t2.dif_gypse = t2.gypse_totaliseur_2 - t1.gypse_totaliseur_1
        t2.dif_dolomite = t2.dolomite_totaliseur_2 - t1.dolomite_totaliseur_1
        t2.dif_compt = t2.compt_totaliseur_2 - t1.compt_totaliseur_1

        # sauvegarder sans boucle infinie
        t2.save(update_fields=[
            "dif_clinker",
            "dif_gypse",
            "dif_dolomite",
            "dif_compt"
        ])
