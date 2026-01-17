from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta, datetime
from django.db.models import Sum, Avg

# Create your models here.


class Totaliseur_1(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)
    post = models.ForeignKey('packing.Post', on_delete=models.CASCADE)
    site = models.ForeignKey('accounts.Site', on_delete=models.CASCADE)
    title = models.CharField(max_length=50, default='')
    compt_totaliseur_1 = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    clinker_totaliseur_1 = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    gypse_totaliseur_1 = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    dolomite_totaliseur_1 = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    date = models.DateField(default=timezone.now, blank=True)
    slug = models.SlugField(default='')
    
    class Meta:
        verbose_name = 'Totaliseur 1'
        verbose_name_plural = 'Totaliseur 1'
        ordering = ('-date', 'post__post')
        
    def generate_title(self):
        date_str = self.date.strftime("%d/%m/%Y")
        shift = {'06H-14H': 'A', '14H-22H': 'B', '06H-18H': 'A', '18H-06H': 'B'}.get(self.post.post, 'C')
        return f"Totaliseur_1_{date_str}_{shift}_{self.site}"
    
    def get_shift_letter(self):
        return {
            '06H-14H': 'A',
            '14H-22H': 'B',
            '22H-06H': 'C',
            '06H-18H': 'A',
            '18H-06H': 'B',
        }.get(self.post.post, '?')
        
    def generate_slug(self):
        return f"{slugify(self.title)}-{int(timezone.now().timestamp())}"

    
    def __str__(self):
        return self.generate_title()
    
    @property
    def make_title(self):
        date_str = self.date.strftime('%d/%m/%Y')
        return f'Broy_{date_str}_{self.get_shift_letter()}_{self.site}'
    
    def save(self, *args, **kwargs):
        
        # if not self.title:
        self.title = self.generate_title()
            
        if not self.slug:
            self.slug = self.generate_slug()
        super().save(*args, **kwargs)
        
        
class Totaliseur_2(models.Model):
    totaliseur = models.ForeignKey(Totaliseur_1, on_delete=models.CASCADE)
    compt_totaliseur_2 = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    clinker_totaliseur_2 = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    gypse_totaliseur_2 = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    dolomite_totaliseur_2 = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    silo_1 = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    silo_2 = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    
    dif_compt = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    dif_clinker = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    dif_gypse = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    dif_dolomite = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.0'))
    slug = models.SlugField(default='')
    
    
    class Meta:
        verbose_name = 'Totaliseur 2'
        verbose_name_plural = 'Totaliseur 2'
        ordering = ('-totaliseur__date', 'totaliseur__post__post')
        
    def get_shift_letter(self):
        return {
            '06H-14H': 'A',
            '14H-22H': 'B',
            '22H-06H': 'C',
            '06H-18H': 'A',
            '18H-06H': 'B',
        }.get(self.totaliseur.post.post, '?')
        
    def generate_title(self):
        date_str = self.totaliseur.date.strftime("%d-%m-%Y")
        shift = {'06H-14H': 'A', '14H-22H': 'B', '06H-18H': 'A', '18H-06H': 'B'}.get(self.totaliseur.post.post, 'C')
        return f"Totaliseur2_{date_str}_{shift}_{self.totaliseur.site}"
        
    def generate_slug(self):
        date_str = self.totaliseur.date.strftime('%d-%m-%Y')
        return f"Totaliseur2_{slugify(date_str)}_{self.get_shift_letter()}_{self.totaliseur.site}-{int(timezone.now().timestamp())}"
    
    def __str__(self):
        return self.generate_title()
    
    @property
    def title(self):
        t1 = self.totaliseur
        date_str = t1.date.strftime('%d/%m/%Y')
        return f'Broy_{date_str}_{self.get_shift_letter()}'
    
    def make_silo(self):
        
        return
    
    
    def save(self, *args, **kwargs):
        t1 = self.totaliseur
        
        if t1:
            self.dif_clinker = Decimal(self.clinker_totaliseur_2 - t1.clinker_totaliseur_1)
            self.dif_gypse = Decimal(self.gypse_totaliseur_2 - t1.gypse_totaliseur_1)
            self.dif_dolomite = Decimal(self.dolomite_totaliseur_2 - t1.dolomite_totaliseur_1)
            self.dif_compt = Decimal(self.compt_totaliseur_2 - t1.compt_totaliseur_1)
                   
        if not self.slug:
            self.slug = self.generate_slug()
        super().save(*args, **kwargs)   
        
        
        
class Production(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)
    post = models.ForeignKey('packing.Post', on_delete=models.CASCADE)
    site = models.ForeignKey('accounts.Site', on_delete=models.CASCADE)
    title = models.CharField(max_length=50, default='')
    production = models.IntegerField(default=0)
    conso = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.0'))
    consignes = models.TextField(default='', blank=True)
    date = models.DateField(default=timezone.now, blank=True)
    slug = models.SlugField(default='')
    
    class Meta:
        verbose_name = 'Rapport de Production'
        verbose_name_plural = 'Rapports de Production'
        ordering = ('-id',)
        
        
    def get_shift_letter(self):
        return {
            '06H-14H': 'A',
            '14H-22H': 'B',
            '22H-06H': 'C',
            '06H-18H': 'A',
            '18H-06H': 'B',
        }.get(self.post.post, '?')
        
    def generate_title(self):
        date_str = self.date.strftime("%d-%m-%Y")
        shift = {'06H-14H': 'A', '14H-22H': 'B', '06H-18H': 'A', '18H-06H': 'B'}.get(self.post.post, 'C')
        return f"Production_{date_str}_{shift}_{self.site}"
        
    def generate_slug(self):
        date_str = self.date.strftime('%d-%m-%Y')
        return f"Production_{slugify(date_str)}_{self.get_shift_letter()}_{self.site}-{int(timezone.now().timestamp())}"
    
    def __str__(self):
        return self.generate_title()
    
    def save(self, *args, **kwargs):
        self.consignes = self.consignes.upper()
        self.title = self.generate_title()
        
        if not self.slug:
            self.slug = self.generate_slug()
        super().save(*args, **kwargs)