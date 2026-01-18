from django import forms
from . models import *


class PackingForm(forms.ModelForm):
    long_shift = forms.BooleanField(
        required=False,
        label="Cocher uniquement si c'est post de 12h"
    )

    class Meta:
        model = Packing
        exclude = ('slug', 'title', 'user', 'site')
        fields = ('post', 'livraison', 'casse', 'vrack', 'date', 'long_shift', 'consignes')
        widgets = {
            'long_shift': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            
            'post':forms.Select(attrs={
                'class': 'form-select',
            }),
            
            'livraison': forms.NumberInput(attrs={
                'class': 'form-control',
            }),
            
            'casse': forms.NumberInput(attrs={
                'class': 'form-control',
            }),
            
            'vrack': forms.NumberInput(attrs={
                'class': 'form-control',
            }),
            
            'date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'  # ✅ format ISO compatible avec HTML5
            ),
            
            'consignes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Entrez les consignes pour le post suivant ici...',
            }),
        }

    def filter_post_queryset(self, long_shift_checked): 
        if long_shift_checked: return Post.objects.filter(duree_post=timedelta(hours=12)) 
        return Post.objects.filter(duree_post=timedelta(hours=8))    
    
    def __init__(self, *args, **kwargs): 
        super().__init__(*args, **kwargs) # Détection du contexte : modification ou soumission 
        long_shift_checked = False 
        if self.data: 
            long_shift_checked = str(self.data.get("long_shift")).lower() in ("on", "true", "1") 
        elif self.instance and getattr(self.instance, "long_shift", False): 
            long_shift_checked = True 
            
        # Filtrage du queryset du champ "post" 
        self.fields["post"].queryset = Post.objects.filter(
            duree_post=timedelta(hours=12 if long_shift_checked else 8) 
        )




    


class PanneForm(forms.ModelForm):
    class Meta:
        model = Pannes
        fields = ('departement', 'start_panne', 'end_panne', 'description', 'solution')
        exclude = ('packing', 'date', 'duree', 'slug')
        
        widgets = {
            'departement': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),
            
            'start_panne': forms.TimeInput(attrs={
                'class': 'form-control',
            }),
            'end_panne': forms.TimeInput(attrs={
                'class': 'form-control',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Décrivez la panne brièvement...',
            }), 
            'solution': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Décrivez la panne brièvement...',
            }), 
        }