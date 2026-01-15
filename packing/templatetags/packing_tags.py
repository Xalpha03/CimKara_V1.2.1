from django import template
register = template.Library()

@register.simple_tag
def get_postes():
    """
    Retourne la liste des postes, couleurs et libellés pour le template.
    """
    return [
        ('06H-14H', 'primary', 'Poste 06H–14H', 'object_post_06h'),
        ('14H-22H', 'success', 'Poste 14H–22H', 'object_post_14h'),
        ('22H-06H', 'warning', 'Poste 22H–06H', 'object_post_22h'),
    ]
