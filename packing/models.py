from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.utils.text import slugify
from accounts.models import Site
from broyage.models import *
from decimal import Decimal




# Create your models here.
print(timezone.now())
class Post(models.Model):
    CHOICES_POST = [
        ('06H-14H', '06H-14H'),
        ('14H-22H', '14H-22H'),
        ('22H-06H', '22H-06H'),
        
        ('06H-18H', '06H-18H'),
        ('18H-06H', '18H-06H'),
    ]
    
    post = models.CharField(max_length=10, choices=CHOICES_POST, default='06H-14H')
    start_post = models.TimeField()
    end_post = models.TimeField()
    duree_post = models.DurationField(default=timedelta())
    
    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Post'
        ordering = ['post']
        
    
    def __str__(self):
        return "Post_{}".format(self.post)
    
    def save(self, *args, **kwargs):
        
        start_time = self.start_post.time() if isinstance(self.start_post, datetime) else self.start_post 
        end_time = self.end_post.time() if isinstance(self.end_post, datetime) else self.end_post
        
        self.start_post = datetime.combine(date.today(), start_time)
        self.end_post = datetime.combine(date.today(), end_time)
        if self.end_post < self.start_post:
            self.end_post += timedelta(days=1)
        
        self.duree_post = self.end_post - self.start_post
        
        return super().save(*args, **kwargs)
    
    
class Packing(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    livraison = models.IntegerField(blank=True, null=True, default=0)
    casse = models.IntegerField(blank=True, null=True, default=0)
    vrack = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=Decimal('0.0'))
    date = models.DateField(default=timezone.now)
    slug = models.SlugField()
    
    
    class Meta:
        verbose_name = 'Packing' 
        verbose_name_plural = 'Packing'
        ordering = ('-date', 'post')
        
        
    def get_shift_letter(self):
        return {
            '06H-14H': 'A',
            '14H-22H': 'B',
            '22H-06H': 'C',
            
            '06H-18H': 'A',
            '18H-06H': 'B',
        }.get(self.post.post, '?')

    def generate_title(self):
        date_text = self.date.strftime('%d/%m/%Y')
        return f"Ens_{date_text}_{self.get_shift_letter()}_{self.site}"

    def generate_slug(self):
        return f"{slugify(self.title)}-{int(datetime.now().timestamp())}"

    def clean_values(self):
        self.livraison = self.livraison or 0
        self.casse = self.casse or 0
        self.vrack = self.vrack or 0.0

    def __str__(self):
        return self.generate_title()
    
    def save(self, *args, **kwargs):
        self.clean_values()
        self.title = self.generate_title()
        if not self.slug:
            self.slug = self.generate_slug()
            
        
        super().save(*args, **kwargs)

    
    
    
DEPARTEMENT_CHOICES = [
    ('MEC', 'MECANIQUE'),
    ('ELECT', 'ELECTRIQUE'),
    ('AUTO', 'AUTOMATISME'),
    ('LAB', 'LABORATOIRE'),
    ('PROD', 'PRODUCTION'),
    ('ARRET PROG', 'ARRET PROGRAMME'),
    ('CEET', 'CEET'),
    ('COMM', 'COMMERCIALE')
]

SECTION_CHOICES = [
    ('broyage', 'broyage'),
    ('packing', 'packing'),
]
class Pannes(models.Model):
    departement = models.CharField(max_length=50, choices=DEPARTEMENT_CHOICES, default="MEC")
    broyage = models.ForeignKey('broyage.Totaliseur_1', on_delete=models.CASCADE, blank=True, null=True)
    packing = models.ForeignKey(Packing, on_delete=models.CASCADE, blank=True, null=True)
    production = models.ForeignKey('broyage.Production', on_delete=models.CASCADE, blank=True, null=True)
    start_panne =models.TimeField()
    end_panne = models.TimeField()
    duree = models.DurationField()
    description = models.TextField()
    solution = models.TextField(blank=True, null=True)
    slug = models.SlugField()
    
    class Meta:
        verbose_name = 'Panne'
        verbose_name_plural = 'Panne'
        # ordering = ['-packing__date', '-broyage__date']
        
    def get_source(self):
        return self.packing or self.broyage or self.production

    
    def get_shift_letter(self):
        source = self.get_source()
        if source is None:
            return None

        raw_post = getattr(source.post, "post", None)
        post = raw_post if isinstance(raw_post, str) else None

        mapping: dict[str, str] = {
            '06H-14H': 'A',
            '14H-22H': 'B',
            '22H-06H': 'C',
            '06H-18H': 'A',
            '18H-06H': 'B'
        }

        return mapping.get(post or "", '?')

    def generate_slug(self):
        source = self.get_source()
        if source is None:
            return None
        date_str = source.date.strftime('%d-%m-%Y')
        return f"Arret_{slugify(date_str)}_{self.get_shift_letter()}_{source.site}-{int(datetime.now().timestamp())}"
    
    

    def calculate_duree(self):
        start_time = datetime.combine(self.date, self.start_panne)
        end_time = datetime.combine(self.date, self.end_panne)
        if end_time < start_time:
            end_time += timedelta(days=1)
        return end_time - start_time
    

    def __str__(self):
        source = self.get_source()
        return f"Arrêt_{source.date}_{source.site}" if source else "Arrêt_inconnu"
    
    @property
    def duree_formatee(self):
        total_seconds = int(self.duree.total_seconds())
        heures = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{heures:02d}:{minutes:02d}"
    
    
    def save(self, *args, **kwargs):
        self.description = self.description.upper()
        self.solution = self.solution.upper() if self.solution else None
        source = self.get_source()
        
        if source:
            self.date = source.date

        if not self.slug:
            self.slug = self.generate_slug()

        self.duree = self.calculate_duree()
        super().save(*args, **kwargs)
