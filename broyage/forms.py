from django import forms
from .models import *
from datetime import timedelta
from django.apps import apps

Post = apps.get_model('packing', 'Post')


class totali_1_Form(forms.ModelForm):
    long_shift = forms.BooleanField(
        required=False,
        label="Cocher uniquement si c'est post de 12h"
    )    
    class Meta:
        model = Totaliseur_1
        fields = ['post', 'compt_totaliseur_1', 'clinker_totaliseur_1', 'gypse_totaliseur_1', 'dolomite_totaliseur_1', 'date', 'long_shift']
        widgets = {
            'long_shift': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            
            'post':forms.Select(attrs={
                'class': 'form-select',
            }),
            'site': forms.Select(attrs={
                'class': 'form-select'
            }),
            'compt_totaliseur_1': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Entrez le compteur broyeur pour commencer'
            }),
            'clinker_totaliseur_1': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Entrez le totaliseur clinker pour commencer'
            }),
            'gypse_totaliseur_1': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Entrez le totaliseur gypse pour commencer'
            }),
            'dolomite_totaliseur_1': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Entrez le totaliseur dolomite pour commencer'
            }),
            'date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'  # ✅ format ISO compatible avec HTML5
            ),
        }
        
class production_Form(forms.ModelForm):
    long_shift = forms.BooleanField(
        required=False,
        label="Cocher uniquement si c'est post de 12h"
    ) 
    class Meta:
        model = Production
        fields = ['post', 'production', 'conso', 'date', 'consignes', 'long_shift']
        widgets = {
            
            'long_shift': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            
            'post':forms.Select(attrs={
                'class': 'form-select',
            }),
            
            'production': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Entrez la production du broyage'
            }),
            
            'conso': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Entrez la consommation du broyage'
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

        
        
class totali_2_Form(forms.ModelForm):

    class Meta:
        model = Totaliseur_2
        fields = ('compt_totaliseur_2', 'clinker_totaliseur_2', 'gypse_totaliseur_2', 'dolomite_totaliseur_2', 'silo_1', 'silo_2')
        widgets = {
            
            'compt_totaliseur_2': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'clinker_totaliseur_2': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'gypse_totaliseur_2': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'dolomite_totaliseur_2': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'silo_1': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'silo_2': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
        }
        

        
        
        
        
        
