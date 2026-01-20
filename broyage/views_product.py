from typing import Any
from django.forms import BaseModelForm
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from .models import Production, Totaliseur_1, Totaliseur_2
from packing.models import Pannes
from django.views.generic import TemplateView, CreateView, UpdateView
from .forms import totali_1_Form, totali_2_Form, production_Form
from packing.forms import PanneForm
from django.db.models import Q, Sum
from datetime import datetime, timedelta, date
from packing.views import get_operational_date, get_operational_month, get_operational_year, get_date_formate
from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.template.loader import get_template
from django.http import HttpResponse
from weasyprint import HTML
import json



# Create your views here.
print(date.today())

class productionHomeView(TemplateView):
    template_name = 'production/production_home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        user = get_object_or_404(User, username=user.username)
        
        search = self.request.GET.get('search')
        is_poste_12h = False
        
        
        profil = getattr(user, 'profil', None)
        if profil:
            role = profil.role
            site = profil.site 
            poste = profil.poste
            section = profil.section    
        else:
            role = None
            site = None
            section =None
        
        filter_productions = Q(site=site)
        filter_pannes = Q(production__site=site)
        
        try:
            if search is not None:
                search_date = datetime.strptime(search, '%d/%m/%Y').date()
            else:
                search_date = date.today()
        
        except ValueError:
            search_date = date.today()
        
        filter_productions &= Q(date=search_date)
        filter_pannes &= Q(production__date=search_date)
        
        obj_pan = Pannes.objects.filter(filter_pannes)
        productions = Production.objects.filter(filter_productions)
        
        if productions.filter(post__post__in=['06H-18H', '18H-06H']).exists():
            is_poste_12h = True
            
            
        temps_arret_total = timedelta()
            
        for p in productions:
            
            temps_arret = Pannes.objects.filter(production=p).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = p.post.duree_post - temps_arret
            
            rendement = Decimal(p.production/(temps_marche.total_seconds()/3600)) if temps_marche.total_seconds() > 0 else Decimal('0')
            rendement = rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            temps_marche_formate = get_date_formate(temps_marche)
            
            temps_arret_total += temps_arret
            
            
            
            setattr(p, 'rendement', rendement)
            setattr(p, 'temps_marche_formate', temps_marche_formate)
            
            
            print(p.production, is_poste_12h, poste)
        context.update({
            'role': role,
            'profil_poste': poste,
            'section': section,
            'object_pannes': obj_pan,
            'is_poste_12h': is_poste_12h,
            'search_date': search_date,
            'temps_arret_total': temps_arret_total,
            
            'object_productions': productions,
            'production_panne': 'production_panne',
            
            'object_productions_06h_14h': productions.filter(post__post='06H-14H'),
            'object_productions_14h_22h': productions.filter(post__post='14H-22H'),
            'object_productions_22h_06h': productions.filter(post__post='22H-06H'),
            
            'object_productions_06h_18h': productions.filter(post__post='06H-18H'),
            'object_productions_18h_06h': productions.filter(post__post='18H-06H'),
        })
        return context

class productionUserView(TemplateView):
    template_name = 'production/user_production.html'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) 

        user = self.kwargs.get('username')
        user = get_object_or_404(User, username=user)
        
        profil = getattr(user, 'profil', None)
        
        if profil:
            role = profil.role
            site = profil.site 
            poste = profil.poste
            section = profil.section    
        else:
            role = None
            site = None
            section =None
        
        search_date = self.request.GET.get('search')
        filter_productions = Q(user=user, site=site)
        
        existe = Production.objects.filter(
            user=user,
            date__month=date.today().month,
            date__year=date.today().year
        ).exists()
                
        if   search_date:
            keywords = [kw.strip() for kw in search_date.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(kw, '%d/%m/%Y').date()
                    filter_productions &= Q(date=search_date)
                    
                except ValueError:
                    if kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            filter_productions &= Q(date__month=kw_int)
                            
                        elif 2000 <= kw_int <= date.today().year:
                            filter_productions &= Q(date__year=kw_int)
        else:
            if not existe:
                filter_productions &= Q(
                    date__month=get_operational_month(),
                    date__year=get_operational_year()
                )
                
            else:
                month = date.today().month
                year = date.today().year
                filter_productions &= Q(date__month=month, date__year=year)
            
        productions = Production.objects.filter(filter_productions).order_by('-date')
        
        temps_arret_total = timedelta()
        temps_marche_total = timedelta()
        production_total = 0
        rendement_moyenne = Decimal()
        conso_moyenne = Decimal()
        conso_total = Decimal()
        
        for p in productions:
            temps_arret = Pannes.objects.filter(production=p).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = p.post.duree_post - temps_arret
            
            rendement = Decimal(p.production/(temps_marche.total_seconds()/3600)) if temps_marche.total_seconds() > 0 else Decimal('0')
            rendement = rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            temps_arret_formate = get_date_formate(temps_arret)
            temps_marche_formate = get_date_formate(temps_marche)
            
            temps_arret_total += temps_arret
            temps_marche_total += temps_marche
            
            production_total += p.production
            rendement_moyenne = Decimal(production_total)/Decimal(temps_marche_total.total_seconds()/3600) if temps_marche_total.total_seconds() > 0 else Decimal('0')
            rendement_moyenne = rendement_moyenne.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            conso_total += Decimal(p.conso) if p.conso else Decimal('0')
            conso_moyenne = conso_total/Decimal(productions.count()) if productions.count() > 0 else Decimal('0')
            conso_moyenne = conso_moyenne.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            
            
            setattr(p, 'rendement', rendement)  
            setattr(p, 'temps_arret_formate', temps_arret_formate)
            setattr(p, 'temps_marche_formate', temps_marche_formate)
            
         
        context.update({
            'role': role,
            'poste': poste,
            'section': section,
            'object_productions': productions,
            'search_date': search_date,
            
            'production_total': production_total,
            'temps_arret_total': temps_arret_total,
            'temps_marche_total': temps_marche_total,
            'rendement_moyenne': rendement_moyenne,
            'conso_moyenne': conso_moyenne,
        })
        return context
    
    
class productionUserPanne(TemplateView):
    template_name = 'production/production_panne_user.html'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)
        
        profil = getattr(user, 'profil', None)
        if profil:
            role = profil.role
            section = profil.section
        else:
            role = None
            section = None
        
        search = self.request.GET.get('search')
        filter_pannes = Q(production__user=user)
        
        existe = Pannes.objects.filter(
            production__user=user,
            production__date__month=date.today().month,
            production__date__year=date.today().year,
        ).exists()
        
        if search:
            keywords = [kw.strip() for kw in search.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(kw, '%d/%m/%Y').date()
                    filter_pannes &= Q(production__date=search_date)
                    
                except ValueError:
                    if kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            filter_pannes &= Q(production__date__month=kw_int)
                            
                        elif 2000 <= kw_int <= date.today().year:
                            filter_pannes &= Q(production__date__year=kw_int)
                            
        else:
            if not existe:
                filter_pannes &= Q(
                    production__date__month=get_operational_month(),
                    production__date__year=get_operational_year()
                )
            else:
                month = date.today().month
                year = date.today().year
                filter_pannes &= Q(production__date__month=month, production__date__year=year)
            
        object_pannes = Pannes.objects.filter(filter_pannes).order_by('-production__date', 'production__post')
        temps_arret_total = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
        
               
        
        print('total panne :', temps_arret_total)
        
        context.update({
            'role': role,
            'section': section,
            'production_panne': 'production_panne',
            'object_pannes': object_pannes,
            'temps_arret_total': temps_arret_total,
        })
        return context
        

class productionAdminView(TemplateView):
    template_name = 'production/production_admin.html'
    
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        user = get_object_or_404(User, username=user.username)
        
        profil = getattr(user, 'profil', None)
        if profil:
            role = profil.role
            site = profil.site 
            section = profil.section
        else:
            role = None
            site = None
            section =None
        
        search_date = self.request.GET.get('search')
        filter_productions = Q(site=site)
        
        existe = Production.objects.filter(
            site=site,
            date__year=date.today().year
        ).exists()
                
        if   search_date:
            keywords = [kw.strip() for kw in search_date.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(kw, '%d/%m/%Y').date()
                    filter_productions &= Q(date=search_date)
                    
                except ValueError:
                    if kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            filter_productions &= Q(date__month=kw_int)
                            
                        elif 2000 <= kw_int <= date.today().year:
                            filter_productions &= Q(date__year=kw_int)
        else:
            if not existe:
                filter_productions &= Q(
                    date__month=get_operational_month(),
                    date__year=get_operational_year()
                )
            else:
                month = date.today().month
                year = date.today().year
                filter_productions &= Q(date__month=month, date__year=year)
            
        productions = Production.objects.filter(filter_productions).order_by('-date')
               
        
        context.update({
            'adm': 'adm',
            'role': role,
            'section': section,
            'object_productions': productions,
            'search_date': search_date,
        })
        return context
    
    
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if request.GET.get('download') == 'pdf':
            context['pdf'] = True

            # Récupération de la date recherchée
            search_date = context.get('search_date')

            # Construction du nom du fichier
            if search_date:
                filename = f"rapport_{search_date.strftime('%d-%m-%Y')}.pdf"
            else:
                filename = "rapport.pdf"

            # Génération du PDF
            template = get_template('production/production_admin_pdf.html')
            html_string = template.render(context)
            pdf_file = HTML(string=html_string,
                            base_url=request.build_absolute_uri()).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response

        return self.render_to_response(context)
    
    
    
class productionAdmin(TemplateView):
    template_name = 'production/production_admin.html'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        user = get_object_or_404(User, username=user.username)
        
        profil = getattr(user, 'profil', None)
        if profil:
            role = profil.role
            site = profil.site 
            section = profil.section
        else:
            role = None
            site = None
            section =None
        
        search_date = self.request.GET.get('search')
        filter_productions = Q(site=site)
        
        existe = Production.objects.filter(
            site=site,
            date__year=date.today().year
        ).exists()
                
        if   search_date:
            keywords = [kw.strip() for kw in search_date.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(kw, '%d/%m/%Y').date()
                    filter_productions &= Q(date=search_date)
                    
                except ValueError:
                    if kw.isalpha():
                        filter_productions &= Q(user__last_name__icontains=str(kw))
                        
                    elif kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            filter_productions &= Q(date__month=kw_int)
                            
                        elif 2000 <= kw_int <= date.today().year:
                            filter_productions &= Q(date__year=kw_int)
        else:
            if not existe:
                filter_productions &= Q(
                    date__year=get_operational_year()
                )
            else:
                year = date.today().year
                filter_productions &= Q(date__year=year)
            
        productions = Production.objects.filter(filter_productions).order_by('-date')
        production_total = 0
        temps_arret_total = timedelta()
        temps_marche_total = timedelta()
        rendement_moyenne = Decimal()
        conso_total = Decimal()
        conso_moyenne = Decimal()
        for p in productions:
            
            temps_arret = Pannes.objects.filter(production=p).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = p.post.duree_post - temps_arret
            
            rendement = Decimal(p.production/(temps_marche.total_seconds()/3600)) if temps_marche.total_seconds() > 0 else Decimal('0')
            rendement = rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            temps_arret_formate = get_date_formate(temps_arret)
            temps_marche_formate = get_date_formate(temps_marche)   
            
            setattr(p, 'rendement', rendement)
            setattr(p, 'temps_arret_formate', temps_arret_formate)
            setattr(p, 'temps_marche_formate', temps_marche_formate)
            
            temps_arret_total += temps_arret
            temps_marche_total += temps_marche
            production_total += p.production if p.production else 0
            rendement_moyenne = Decimal(production_total)/Decimal(temps_marche_total.total_seconds()/3600) if temps_marche_total.total_seconds() > 0 else Decimal('0')
            rendement_moyenne = rendement_moyenne.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            conso_total += Decimal(p.conso) if p.conso else Decimal('0')
            conso_moyenne = conso_total/Decimal(productions.count()) if productions.count() > 0 else Decimal('0')
            conso_moyenne = conso_moyenne.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            print('temps_arret :', temps_arret)
        
        
        context.update({
            # 'adm': 'adm',
            'role': role,
            'section': section,
            'object_productions': productions,
            'search_date': search_date,
            
            'production_total': production_total,
            'temps_arret_total': temps_arret_total,
            'temps_marche_total': temps_marche_total,
            'rendement_moyenne': rendement_moyenne,
            'conso_moyenne': conso_moyenne,
            
        })
        return context
    
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if request.GET.get('download') == 'pdf':
            context['pdf'] = True

            # Récupération de la date recherchée
            search_date = context.get('search_date')

            # Construction du nom du fichier
            if search_date:
                filename = f"rapport_{search_date.strftime('%d-%m-%Y')}.pdf"
            else:
                filename = "rapport.pdf"

            # Génération du PDF
            template = get_template('production/production_admin_pdf.html')
            html_string = template.render(context)
            pdf_file = HTML(string=html_string,
                            base_url=request.build_absolute_uri()).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response

        return self.render_to_response(context)


class productionPanneAdmin(TemplateView):
    template_name = 'production/production_panne_admin.html'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        user = get_object_or_404(User, username=user.username)
        
        profil = getattr(user, 'profil', None)
        if profil:
            role = profil.role
            site = profil.site 
            section = profil.section
        else:
            role = None
            site = None
            section =None
        
        search = self.request.GET.get('search')
        filter_pannes = Q(production__site=site)
        
        existe = Pannes.objects.filter(
            production__site=site,
            production__date__year=date.today().year,
        ).exists()
        
        if search:
            keywords = [kw.strip() for kw in search.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(kw, '%d/%m/%Y').date()
                    filter_pannes &= Q(production__date=search_date)
                    
                except ValueError:
                    if kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            filter_pannes &= Q(production__date__month=kw_int)
                            
                        elif 2000 <= kw_int <= date.today().year:
                            filter_pannes &= Q(production__date__year=kw_int)
                            
        else:
            if not existe:
                filter_pannes &= Q(
                    production__date__year=get_operational_year()
                )
            else:
                filter_pannes &= Q(
                    production__date__year=date.today().year
                )
            
        object_pannes = Pannes.objects.filter(filter_pannes).order_by('-production__date', 'production__post')
        temps_arret_total = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
                

        
        context.update({
            # 'adm': 'adm',
            'role': role,
            'section': section,
            'production_panne': 'production_panne',
            'object_pannes': object_pannes,
            'temps_arret_total': temps_arret_total,
        })
        return context
    
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if request.GET.get('download') == 'pdf':
            context['pdf'] = True

            # Récupération de la date recherchée
            search_date = context.get('search_date')

            # Construction du nom du fichier
            if search_date:
                filename = f"rapport_{search_date.strftime('%d-%m-%Y')}.pdf"
            else:
                filename = "rapport.pdf"

            # Génération du PDF
            template = get_template('production/production_panne_admin_pdf.html')
            html_string = template.render(context)
            pdf_file = HTML(string=html_string,
                            base_url=request.build_absolute_uri()).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response

        return self.render_to_response(context)

class ajoutProduction(CreateView):
    model = Production
    form_class = production_Form
    template_name = 'production/formulaire.html'
    success_url = reverse_lazy('broyage:production_home')
    
    def form_valid(self, form):
        user = self.request.user
        profil = getattr(user, 'profil', None)
        if profil:
            site = profil.site
        else:
            form.instance = None
            site = None
        
        form.instance.user=user
        form.instance.site=site
        
        post = form.cleaned_data.get('post')
        date = form.cleaned_data.get('date')
        
        existe = Production.objects.filter(post=post, date=date, site=site).exists()
        if existe:
            messages.warning(self.request, "⚠️ Une production pour ce poste existe déjà aujourd’hui.")
            return redirect('broyage:ajout_production')

        messages.success(self.request, "✅ Production ajoutée avec succès.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ajout_production']= 'ajout_production'
        return context
    
class ajoutProductionPannes(CreateView):
    model = Pannes
    form_class = PanneForm
    template_name = 'production/formulaire.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('broyage:production_home')
    
    def form_valid(self, form):
        slug = self.kwargs.get('slug')
        
        p = get_object_or_404(Production, slug=slug)
        
        form.instance.production=p
        
        return super().form_valid(form)
    
    def get_success_url(self):
        slug = self.kwargs.get('slug')
        base_url = reverse_lazy('broyage:ajout_production_panne', kwargs={'slug': slug})
        return f'{base_url}'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug')
        
        p = get_object_or_404(Production, slug=slug)
        object_pannes = Pannes.objects.filter(production=p).order_by('pk')
        
        temps_arret_total = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
        total_temps_arret_formate = get_date_formate(temps_arret_total)
             
        context.update({
            'production_panne': 'production_panne',
            'object_pannes': object_pannes,
            'temps_arret_total': temps_arret_total,
            'total_temps_arret_formate': total_temps_arret_formate,
        })
        return context
    
class updateProduction(UpdateView):
    model = Production
    template_name = 'production/formulaire.html'
    form_class = production_Form
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    context_object_name = 'update_production'
    success_url = reverse_lazy('broyage:production_home')





    

  