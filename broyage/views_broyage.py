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



class broyageHomeView(TemplateView):
    template_name = 'broyage/broyage_home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        profil = getattr(user, "profil", None)

        if profil:
            role = profil.role
            site = profil.site
            poste = profil.poste
            section = profil.section
            
        else:
            role = None
            site = None
            section = None
            poste = None

        search = self.request.GET.get('search', None)
        next_day = None
        is_poste_12h = False
        
        filter_tota_1 = Q(site=site)
        filter_tota_2 = Q(totaliseur__site=site)
        filter_pannes = Q(broyage__site=site)
        
        try:
            if search is not None:
                search_date = datetime.strptime(search, '%d/%m/%Y').date()
                next_day = search_date + timedelta(days=1)
                print("yes")
            else:
                search_date = get_operational_date()
                
                
            
        except ValueError:
            search_date = date.today()
            next_day = search_date + timedelta(days=1)
            
                       
            
        filter_pannes &= Q(broyage__date=search_date)
        filter_tota_1 &= Q(date=search_date)
        filter_tota_2 &= Q(totaliseur__date=search_date)
        
        obj_pan = Pannes.objects.filter(filter_pannes)
        t1 = Totaliseur_1.objects.filter(filter_tota_1)
        t2 = Totaliseur_2.objects.filter(filter_tota_2)
        
        if t1.filter(post__post__in=['06H-18H', '18H-06H']).exists():
            is_poste_12h = True
    
        print('t1 ====> :', t1, "t2 ====> :", t2)
        total_temps_marche = timedelta()
        temps_marche = timedelta()
        total_temps_arret = timedelta()
        total_temps_arret_formate = str()
        
        for t in t1:
            temps_arret_t1 = obj_pan.filter(broyage=t).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche_t1 = t.post.duree_post - temps_arret_t1
            
            temps_marche_formate = get_date_formate(temps_marche_t1)

            
            setattr(t, 'temps_marche_formate', temps_marche_formate)
        
        for t in t2:
            temps_arret = obj_pan.filter(broyage=t.totaliseur).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = t.totaliseur.post.duree_post - temps_arret
            
            production = sum((t.dif_clinker, t.dif_gypse, t.dif_dolomite))
            production = Decimal(production).quantize(Decimal('0'), rounding=ROUND_HALF_UP) if production else Decimal('0')
            rendement = Decimal(production)/Decimal(temps_marche.total_seconds()/3600) if temps_marche.total_seconds() > 0 else Decimal('0')
            rendement = rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            conso = Decimal(t.dif_compt/production).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if production else Decimal('0')
                               
            setattr(t, "production", production)
            setattr(t, 'rendement', rendement)
            setattr(t, 'conso', conso)
            
            
            if temps_arret:
                total_temps_arret += temps_arret
            else:
                total_temps_arret = timedelta()
                
             
            total_temps_arret_formate = get_date_formate(total_temps_arret)      
        
        
        context.update({
            'role': role,
            'broyage_panne': 'broyage_panne',
            'object_pannes': obj_pan,
            'search_date': search_date,
            'poste': poste,
            'section': section,
            'is_poste_12h': is_poste_12h,

            
            'object_pannes': obj_pan,
            'object_totaliseur_1': t1,
            'object_totaliseur_2': t2,
            'temps_arret_total': total_temps_arret,
            'total_temps_arret_formate': total_temps_arret_formate,
            
            'totaliseur_1_06h_14h': t1.filter(post__post='06H-14H'),
            'totaliseur_1_14h_22h': t1.filter(post__post='14H-22H'),
            'totaliseur_1_22h_06h': t1.filter(post__post='22H-06H'),
            
            'totaliseur_1_06h_18h': t1.filter(post__post='06H-18H'),
            'totaliseur_1_18h_06h': t1.filter(post__post='18H-06H'),
            
            'totaliseur_2_06h_14h': t2.filter(totaliseur__post__post='06H-14H'),
            'totaliseur_2_14h_22h': t2.filter(totaliseur__post__post='14H-22H'),
            'totaliseur_2_22h_06h': t2.filter(totaliseur__post__post='22H-06H'),
            
            'totaliseur_2_06h_18h': t2.filter(totaliseur__post__post='06H-18H'),
            'totaliseur_2_18h_06h': t2.filter(totaliseur__post__post='18H-06H'),
        })
        
        return context

class broyageUserView(TemplateView):
    template_name = 'broyage/user_broyage.html'
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        search = self.request.GET.get('search')
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)
        
        profil = getattr(user, 'profil', None)
        if profil:
            role = profil.role
        else:
            role = None
        # Base filter
        filter_pannes = Q(broyage__user=user)
        filter_totaliseur_2 = Q(totaliseur__user=user)
        
        existe = Totaliseur_2.objects.filter(
            totaliseur__user=user,
            totaliseur__date__month=date.today().month,
            totaliseur__date__year=date.today().year
        ).exists()
        
        
        if search:
            keywords = [kw.strip() for kw in search.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    # recherche par date exacte
                    search_date = datetime.strptime(kw, '%d/%m/%Y').date()
                    filter_pannes &= Q(broyage__date=search_date)
                    filter_totaliseur_2 &= Q(totaliseur__date=search_date)
                except ValueError:
                   
                    # recherche par mois ou année
                    if kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            filter_pannes &= Q(broyage__date__month=kw_int)
                            filter_totaliseur_2 &= Q(totaliseur__date__month=kw_int)
                        elif 2000 <= kw_int <= datetime.now().year:
                            filter_pannes &= Q(broyage__date__year=kw_int)
                            filter_totaliseur_2 &= Q(totaliseur__date__year=kw_int)
        else:
            # par défaut : mois et année courants
            if not existe:
                filter_totaliseur_2 &= Q(
                    totaliseur__date__month=get_operational_month(),
                    totaliseur__date__year=get_operational_year()
                )
                print('yse')
            
            else:
                filter_totaliseur_2 &= Q(
                    totaliseur__date__month=date.today().month,
                    totaliseur__date__year=date.today().year
                )

        t2 = Totaliseur_2.objects.filter(filter_totaliseur_2)
        pan = Pannes.objects.filter(filter_pannes)

        total_production = int()
        total_rendement = Decimal()
        total_temps_marche = timedelta()
        total_dif_compt = Decimal()
        total_conso = Decimal()
        total_temps_arret = timedelta()
        total_temps_arret_formate = str()
        total_temps_marche = timedelta()
        total_temps_marche_formate = str()
        
        for obj in t2:
            
            temps_arret = pan.filter(broyage=obj.totaliseur).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = obj.totaliseur.post.duree_post - temps_arret
            
            production = int(sum((obj.dif_clinker, obj.dif_gypse, obj.dif_dolomite)))
            rendement = Decimal(production)/Decimal(temps_marche.total_seconds()/3600) if temps_marche.total_seconds() > 0 else Decimal('0')
            conso = Decimal(obj.dif_compt/production) if production else Decimal('0')
            
            
            # Calcul de temps de arret
            temps_arret_formate = get_date_formate(temps_arret)
            
            
            # Calcul de temps de marche
            
            temps_marche_formate = get_date_formate(temps_marche)
                        
            # obj.production = production
            setattr(obj, "production", production)
            setattr(obj, 'rendement', rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) 
            setattr(obj, 'conso', conso)
            setattr(obj, 'temps_arret_formate', temps_arret_formate)
            setattr(obj, 'temps_marche_formate', temps_marche_formate)
            
            
            # ====================================== Calcul des valeur total et moyenne =============================
            total_production += production
            total_production =total_production
            
            total_temps_marche += temps_marche
            total_rendement = Decimal(total_production)/Decimal(total_temps_marche.total_seconds()/3600)
            total_rendement =total_rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            total_dif_compt += obj.dif_compt
            total_conso = Decimal(total_dif_compt/total_production) if total_production > 0 else Decimal('0')
            total_conso = total_conso.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            
            # Calcul de temps d'arrêt total
            total_temps_arret += temps_arret
            total_temps_arret_formate = get_date_formate(total_temps_arret)
            
            # Calcul de temps d'arrêt total
            total_temps_marche_formate = get_date_formate(total_temps_marche)
                  


        context.update({
            'role': role,
            'object_totaliseur_2': t2,
            
            'total_production': total_production,
            'total_rendement': total_rendement,
            'total_conso': total_conso,
            'total_temps_arret': total_temps_arret,
            'total_temps_marche': total_temps_marche,
            'total_temps_arret_formate': total_temps_arret_formate,
            'total_temps_marche_formate': total_temps_marche_formate,
        })
        return context
        
class broyagePanneUser(TemplateView):
    template_name = 'broyage/broyage_panne_user.html'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.kwargs.get('username')
        search = self.request.GET.get('search')
        
        user = get_object_or_404(User, username=user)
        profil = getattr(user, 'profil', None)
        if profil:
            role = profil.role
            section = profil.section
        else:
            role = None
            section =None
        
        filter_pannes = Q(broyage__user=user)
        
        existe = Pannes.objects.filter(
            broyage__user=user,
            broyage__date__month=date.today().month,
            broyage__date__year=date.today().year
        ).exists()
        
        search_date = timedelta()
        if search:
            keywords = [kw.strip() for kw in search.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(kw, '%d/%m/%Y').date()
                    filter_pannes &= Q(broyage__date=search_date)
                    
                except ValueError:
                    if kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            search_date = datetime.strptime(str(kw_int), '%m').date()
                            search_date = search_date.month
                            filter_pannes &= Q(broyage__date__month=kw_int)
                            
                        elif 2000 <= kw_int <= datetime.now().year:
                            search_date = datetime.strptime(str(kw_int), '%Y').date()
                            search_date = search_date.year
                            filter_pannes &= Q(broyage__date__year=kw_int)
                            
        else:
            if not existe:
                filter_pannes &= Q(
                    broyage__date__month=get_operational_month(),
                    broyage__date__year=get_operational_year()
                )
            
            else:
                search_date =  date.today().month
                filter_pannes &= Q(
                    broyage__date__month=search_date,
                    broyage__date__year = date.today().year
                )
                
        object_pannes = Pannes.objects.filter(filter_pannes).order_by('-broyage__date', 'broyage__post')
        
        temps_arret_total = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
        
        
        total_temps_arret_formate = get_date_formate(temps_arret_total)
        
        context.update({
            # 'adm': 'adm',
            'role': role,
            'section': section,
            'broyage_panne': 'broyage_panne',
            'search_date': search_date,
            'object_pannes': object_pannes,
            'total_temps_arret_formate':total_temps_arret_formate,
            'temps_arret_total': temps_arret_total,
            
        })
        return context
    
class broyageAdmin(TemplateView):
    template_name = 'broyage/broyage_admin.html'
    
    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        user = get_object_or_404(User, username=user.username)
        
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
        
        
        filter_totaliseur = Q(totaliseur__site=site)
        filter_pannes = Q(broyage__site=site)
        
        existe = Totaliseur_2.objects.filter(
            totaliseur__site=site,
            totaliseur__date__year=date.today().year
        ).exists()
        
        search_date = self.request.GET.get('search')
        
        if search_date:
            keywords = [kw.strip() for kw in search_date.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(kw, '%d/%m/%Y').date()
                    filter_pannes &= Q(broyage__date=search_date)
                    filter_totaliseur &= Q(totaliseur__date=search_date)
                    
                except ValueError:
                    if kw.isalpha():
                        filter_totaliseur &= Q(totaliseur__user__last_name__icontains=str(kw))
                    elif kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            filter_pannes &= Q(broyage__date__month=kw_int)
                            filter_totaliseur &= Q(totaliseur__date__month=kw_int)
                            search_date = datetime.strptime(str(kw_int), '%m').month
                        elif 2000 <= kw_int <= date.today().year:
                            filter_pannes &= Q(broyage__date__year=kw_int)
                            filter_totaliseur &= Q(totaliseur__date__year=kw_int)
                            
        else:
            
            if not existe:
                search_date = get_operational_year()
                filter_pannes &= Q(broyage__date__year=search_date)
                filter_totaliseur &= Q(totaliseur__date__year=search_date)
            
            else:
                search_date = date.today().year
                filter_pannes &= Q(broyage__date__year=date.today().year)
                filter_totaliseur &= Q(totaliseur__date__year=date.today().year)
                
        print(search_date)              
        t2 = Totaliseur_2.objects.filter(filter_totaliseur)
        pan = Pannes.objects.filter(filter_pannes)
        
        
        total_production = int()
        total_rendement = Decimal()
        total_conso = Decimal()
        total_dif_compt =Decimal()
        total_temps_arret = timedelta()
        total_temps_marche = timedelta()
        total_temps_arret_formate = str()
        total_temps_marche_formate = str()
        
        for t in t2:
            temps_arret = pan.filter(broyage=t.totaliseur).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = t.totaliseur.post.duree_post - temps_arret
            
            production = int(sum((t.dif_clinker, t.dif_gypse, t.dif_dolomite)))
            rendement = Decimal(production)/Decimal(temps_marche.total_seconds()/3600) if temps_marche.total_seconds() > 0 else Decimal('0')
            conso = Decimal(t.dif_compt/production) if production > 0 else Decimal('0')
            
            # Calcul de temps de arret
            temps_arret_formate = get_date_formate(temps_arret)
            
            
            # Calcul de temps de marche
            temps_marche_formate = get_date_formate(temps_marche)
            
            setattr(t, 'production', production)
            setattr(t, 'rendement', rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            setattr(t, 'conso', conso.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            setattr(t, 'temps_arret_formate', temps_arret_formate)
            setattr(t, 'temps_marche_formate', temps_marche_formate)
            
            
            # ========================================== Calcul des valeurs total et moyenne =================================
            total_temps_arret += temps_arret
            total_temps_marche += temps_marche
            total_dif_compt += t.dif_compt
            
            total_production += production
            total_production = total_production
            
            total_rendement = Decimal(total_production)/Decimal(total_temps_marche.total_seconds()/3600) if total_temps_marche.total_seconds() > 0 else Decimal('0')
            total_rendement = total_rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            total_conso = Decimal(total_dif_compt/total_production) if total_production > 0 else Decimal('0')
            total_conso = total_conso.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Calcul de temps de arret
            total_temps_arret_formate = get_date_formate(total_temps_arret)
            
            
            # Calcul de temps de marche            
            total_temps_marche_formate = get_date_formate(total_temps_marche)
            
            print(total_temps_arret, total_temps_marche)
            
            
        context.update({
            'role': role,
            'poste':poste,
            'section': section,
            'search_date': search_date,
            'object_totaliseur_2': t2,
            'total_production': total_production,
            'total_rendement': total_rendement,
            'total_conso': total_conso,
            'total_temps_arret': total_temps_arret,
            'total_temps_marche': total_temps_marche,
            'total_temps_arret_formate': total_temps_arret_formate,
            'total_temps_marche_formate': total_temps_marche_formate
        })
        return context
    
    
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        # Vérifie si l’utilisateur demande le PDF
        if request.GET.get('download') == 'pdf':
            context['pdf'] = True  # Indique au template que c’est pour le PDF
            template = get_template('broyage/broyage_admin_pdf.html')
            html_string = template.render(context)

            pdf_file = HTML(string=html_string,
                            base_url=request.build_absolute_uri()).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="rapport.pdf"'
            return response

        # Sinon, retour normal HTML
        return self.render_to_response(context)  
class broyagePanneAdmin(TemplateView):
    template_name = 'broyage/broyage_panne_admin.html'
    
    
    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user = get_object_or_404(User, username=user.username)
        profil = getattr(user, 'profil', None)
        
        if profil:
            site = profil.site
            role = profil.role
            poste = profil.poste
            section = profil.section
        else:
            site = None
            role = None
            section =None
 
        search = self.request.GET.get('search')
        filter_pannes = Q(broyage__site=site)
                  
        existe = Pannes.objects.filter(
            broyage__site=site,
            broyage__date__year=date.today().year
        ).exists()
        
        if search:
            keywords = [kw.strip() for kw in search.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(search, '%d/%m/%Y').date()
                    filter_pannes &= Q(broyage__date=search_date)
                    
                except ValueError:
                    if kw.isalpha():
                        filter_pannes &= Q(broyage__user__last_name__icontains=str(kw))
                    elif kw.isdigit():
                        kw_int = int(kw)
                        
                        if 1 <= kw_int <= 12:
                            filter_pannes &= Q(broyage__date__month=kw_int)
                            
                        elif 2000 <= kw_int <= date.today().year:
                            filter_pannes &= Q(broyage__date__year=kw_int)
        else:
            if not existe:
                filter_pannes &= Q(
                    broyage__date__year=get_operational_year()
                )
                print('yes', get_operational_year())
                
            else:
                filter_pannes &= Q(
                    broyage__date__year=date.today().year
                ) 
                print('no')
                
        object_pannes = Pannes.objects.filter(filter_pannes).order_by('-broyage__date', 'broyage__post')
        
        total_temps_arret = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
        
        total_temps_arret_formate = get_date_formate(total_temps_arret)
        
            
        
        
        context.update({
            # 'admin': 'admin',
            'role': role,
            'section': section,
            'poste': poste,
            'total': 'total',
            'broyage_panne': 'broyage_panne',
            'object_pannes': object_pannes,
            'temps_arret_total': total_temps_arret,
            'total_temps_arret_formate': total_temps_arret_formate
            
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
            template = get_template('broyage/broyage_panne_admin_pdf.html')
            html_string = template.render(context)
            pdf_file = HTML(string=html_string,
                            base_url=request.build_absolute_uri()).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response

        return self.render_to_response(context)
    
class ajoutTotaliseur_1(CreateView):
    model = Totaliseur_1
    form_class = totali_1_Form
    template_name = 'broyage/formulaire.html'
    success_url = reverse_lazy('broyage:broyage_home')
    
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
        
        existe = Totaliseur_1.objects.filter(post=post, date=date, site=site).exists()
        if existe:
            messages.warning(self.request, "⚠️ Un totaliseur pour ce poste existe déjà aujourd’hui.")
            return redirect('broyage:ajout_totali_1')

        messages.success(self.request, "✅ Totaliseur ajouté avec succès.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ajout_totali_1']= 'ajout_totali_1'
        return context
    
class ajoutTotaliseur_2(CreateView):
    model = Totaliseur_2
    form_class = totali_2_Form
    template_name = 'broyage/formulaire.html'
    success_url = reverse_lazy('broyage:broyage_home')
    
    
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        slug = self.kwargs.get('slug')
        t1 = get_object_or_404(Totaliseur_1, slug=slug)
        form.instance.totaliseur=t1
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['ajout_totali_2']='ajout_totali_2'
        return context

class ajoutBroyagePannes(CreateView):
    model = Pannes
    form_class = PanneForm
    template_name = 'broyage/formulaire.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('broyage:broyage_home')
    
    def form_valid(self, form):
        slug = self.kwargs.get('slug')
        
        t = get_object_or_404(Totaliseur_1, slug=slug)
        
        form.instance.broyage=t
        
        return super().form_valid(form)
    
    def get_success_url(self):
        slug = self.kwargs.get('slug')
        base_url = reverse_lazy('broyage:ajout_panne', kwargs={'slug': slug})
        return f'{base_url}'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug')
        
        t1 = get_object_or_404(Totaliseur_1, slug=slug)
        object_pannes = Pannes.objects.filter(broyage=t1).order_by('pk')
        
        temps_arret = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
        total_temps_arret_formate = get_date_formate(temps_arret)
        print(temps_arret)
             
        context.update({
            'broyage_panne': 'broyage_panne',
            'object_pannes': object_pannes,
            'total_temps_arret_formate': total_temps_arret_formate,
        })
        return context
     
class updateTotaliseur_1(UpdateView):
    model = Totaliseur_1
    form_class = totali_1_Form
    slug_field = 'slug'                # champ du modèle
    slug_url_kwarg = 'slug'            # paramètre attendu dans l’URL
    template_name = 'broyage/formulaire.html'
    context_object_name = 'update_totali_1'
    success_url = reverse_lazy('broyage:broyage_home')  # redirection après POST
    
    def form_valid(self, form):
        print("POST data:", self.request.POST)
        return super().form_valid(form)
    
class updateTotaliseur_2(UpdateView):
    model = Totaliseur_2
    form_class = totali_2_Form
    template_name = 'broyage/formulaire.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    context_object_name = 'update_totali_2'
    success_url = reverse_lazy('broyage:broyage_home')
      
class updatePanne(UpdateView):
    model = Pannes
    template_name = 'broyage/formulaire.html'
    form_class = PanneForm
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('broyage:broyage_home')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug')
        
        object_pannes = Pannes.objects.filter(slug=slug)
        temps_arret = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
        total_temps_arret_formate = get_date_formate(temps_arret)
        
        context.update({
            'broyage_panne': 'broyage_panne',
            'update_panne': 'update_panne',
            'object_pannes': object_pannes,
            'total_temps_arret_formate': total_temps_arret_formate,
        })
        return context
    
    def get_success_url(self) -> str:
        slug = self.kwargs.get('slug')
        print(slug)
        base_url = reverse_lazy('broyage:update_panne', kwargs={'slug': slug})
        return f'{base_url}'

class dashboard(TemplateView):
    template_name = 'broyage/dashboard.html'
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        profil = getattr(user, 'profil', None)
        if profil:
            role = profil.role
            site = profil.site 
            section = profil.section
        else:
            role = None
            site = None
            section =None
        
        
        filter_totaliseur = Q(totaliseur__site=site)
        # filter_pannes = Q(broyage__site=site)
        
        existe = Totaliseur_2.objects.filter(
            totaliseur__site=site,
            totaliseur__date__year=date.today().year
        ).exists()
        
        search = self.request.GET.get('search')
        if search:
            keywords = [kw.strip() for kw in search.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(kw, '%d/%m/%Y').date()
                    # filter_pannes &= Q(broyage__date=search_date)
                    filter_totaliseur &= Q(totaliseur__date=search_date)
                    
                except ValueError:
                    if kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            # filter_pannes &= Q(broyage__date__month=kw_int)
                            filter_totaliseur &= Q(totaliseur__date__month=kw_int)
                        elif 2000 <= kw_int <= date.today().year:
                            # filter_pannes &= Q(broyage__date__year=kw_int)
                            filter_totaliseur &= Q(totaliseur__date__year=kw_int)
                            
        else:
            
            if not existe:
                search_date = get_operational_year()
                # filter_pannes &= Q(broyage__date__year=search_date)
                filter_totaliseur &= Q(totaliseur__date__year=search_date)
            
            else:
                # filter_pannes &= Q(broyage__date__year=date.today().year)
                filter_totaliseur &= Q(totaliseur__date__year=date.today().year)

        t2 = Totaliseur_2.objects.filter(filter_totaliseur)
        # pan = Pannes.objects.filter(filter_pannes)

        total_production = Decimal()
        moyenne_rendement = Decimal()
        total_temps_marche = timedelta()
        total_dif_compt = Decimal()
        moyenne_conso = Decimal()
        total_temp_arret = timedelta()
        total_temps_arret_formate = str()
        total_temp_marche = timedelta()
        total_temps_marche_formate = str()
        labels, production, rendement, consomation, temp_arret = [], [], [], [], []
        
        for obj in t2:
            temps_arret = Pannes.objects.filter(broyage=obj.totaliseur).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = obj.totaliseur.post.duree_post - temps_arret
            
            product = sum((obj.dif_clinker, obj.dif_gypse, obj.dif_dolomite))
            rend = Decimal(product)/Decimal(temps_marche.total_seconds()/3600)
            conso = Decimal(obj.dif_compt/product)
            
            
            # Calcul de temps de arret
            heure = int(temps_arret.total_seconds())//3600
            minute = int(temps_arret.total_seconds())%3600 // 60
            temps_arret_formate = f'{heure:02d}:{minute:02d}'
            
            
            # Calcul de temps de marche
            temp_march = obj.totaliseur.post.duree_post - temps_arret
            heure = int(temp_march.total_seconds())//3600
            minute = int(temp_march.total_seconds())%3600 // 60
            temps_marche_formate = f'{heure:02d}:{minute:02d}'
                        
            
            
            # obj.production = production
            labels.append(obj.totaliseur.date.strftime("%d/%m/%Y"))
            production.append(float(product))
            rendement.append(float(rend))
            consomation.append(float(conso))
            
            
            # ====================================== Calcul des valeur total et moyenne =============================
            total_production += product
            total_production =total_production.quantize(Decimal('0'), rounding=ROUND_HALF_UP)
            
            total_temps_marche += temp_march
            moyenne_rendement = Decimal(total_production)/Decimal(total_temps_marche.total_seconds()/3600)
            moyenne_rendement =moyenne_rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            total_dif_compt += obj.dif_compt
            moyenne_conso = Decimal(total_dif_compt/total_production)
            moyenne_conso = moyenne_conso.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            
            # Calcul de temps d'arrêt total
            total_temp_arret += temps_arret
            heure = int(total_temp_arret.total_seconds())//3600
            minute = int(total_temp_arret.total_seconds())%3600 // 60
            total_temps_arret_formate = f'{heure:02d}:{minute:02d}'
            total_temps_arret_formate = total_temps_arret_formate
            
            # Calcul de temps d'arrêt total
            total_temp_marche += temps_marche
            heure = int(total_temp_marche.total_seconds())//3600
            minute = int(total_temp_marche.total_seconds())%3600 // 60
            total_temps_marche_formate = f'{heure:02d}:{minute:02d}'
            total_temps_marche_formate = total_temps_marche_formate
            
            print(rendement)
                    


        context.update({
            'broyage': 'broyage',
            'object_totaliseur_2': t2,
            "labels": json.dumps(labels),
            "production": json.dumps(production),
            "rendement": json.dumps(rendement),
            "consomation": json.dumps(consomation),
            
            'total_production': total_production,
            'moyenne_rendement': moyenne_rendement,
            'moyenne_conso': moyenne_conso,
            'total_temps_arret_formate': total_temps_arret_formate,
            'total_temps_marche_formate': total_temps_marche_formate,
        })
        return context    
    