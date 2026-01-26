

from typing import Any
from django.urls import reverse_lazy
from django.shortcuts import redirect
from datetime import datetime, time, timedelta, date
from django.views.generic import TemplateView, CreateView, UpdateView
from .models import *
from django.db.models import Q, Sum, Max
from decimal import ROUND_HALF_UP, Decimal
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from broyage.models import Totaliseur_2
from django.template.loader import get_template
from django.http import HttpResponse
from weasyprint import HTML
from .forms import *
import json

# Create your views here.


# def get_operational_date():
#     now = datetime.now()
#     seuil = time(11, 10)  # 10h10 du matin
#     if now.time() < seuil:
#         return (now - timedelta(days=1)).date()
#     return now.date()

def get_operational_date():
    """
    Retourne la date d'exploitation (logique industrielle)
    - Si on est entre 00h00 et 05h59 → on considère qu'on est encore sur la veille.
    - Sinon, on prend la date du jour.
    """
    now = timezone.localtime()
    current_time = now.time()

    # Si on est avant 6h → c'est encore la journée d'hier
    if current_time < time(6, 15):
        operational_date = (now - timedelta(days=1)).date()
    else:
        operational_date = now.date()

    return operational_date
print('operational date: ', get_operational_date())

def get_operational_month():
    mois = date.today().month
    # Si on est en janvier, le mois opérationnel est décembre (12)
    return 12 if mois == 1 else mois - 1

print('mointh: ', get_operational_month())

def get_operational_year():
    annee = date.today().year
    # Si on est en janvier, l'année opérationnelle est l'année précédente
    return annee - 1 
print('year: ', get_operational_year())


def get_date_formate(t=None):
    if t is None:
        t = timedelta()
    total_seconds = t.total_seconds()
    heure = int(total_seconds)//3600
    minute = int(total_seconds)%3600//60
    return f'{heure:02d}:{minute:02d}'


class homeView(TemplateView):
    template_name = 'home_page.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect('account:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        context.update(self.context_packing())
        context.update(self.context_broyage())
        context.update(self.context_production())
        
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
            template = get_template('home_page_pdf.html')
            html_string = template.render(context)
            pdf_file = HTML(string=html_string,
                            base_url=request.build_absolute_uri()).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response

        return self.render_to_response(context)
    
    def context_packing(self):
        user = self.request.user
        profil = getattr(user, 'profil', None)
        if profil:
            site = profil.site
            section = profil.section
        else:
            site = None
            
        search_date = self.request.GET.get('search')
        filter_pack = Q(site=site)
        filter_pann = Q(packing__site=site)
        if search_date:
            try:
                search_date = datetime.strptime(search_date, '%d/%m/%Y').date()
            except ValueError:
                search_date = None         
 
        else:
            existe = Packing.objects.filter(date=date.today(), site=site).exists()
            
            if existe:
                search_date = date.today()
            
            else:
                last_packing = Packing.objects.aggregate(Max('date'))['date__max']
                last_broyage = Totaliseur_2.objects.aggregate(Max('totaliseur__date'))['totaliseur__date__max']
                
                if last_broyage and last_packing:
                    search_date = max(last_packing, last_broyage)
                else:
                    search_date = None

                    
        filter_pack &= Q(date=search_date)
        filter_pann &= Q(packing__date=search_date)
        
        pack = Packing.objects.filter(filter_pack)
        pann = Pannes.objects.filter(filter_pann)
        
        
        livraison_total = int()
        total_vrack = Decimal()
        total_sum_liv_vrack = Decimal()
        total_ensache = int()
        total_casse = int()
        total_tx_casse = Decimal()
        temps_marche_total = timedelta()
        temps_marche_total_format = str()
        total_rendement = Decimal()
        
        for t in pack:
            temps_arret = pann.filter(packing=t).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = t.post.duree_post - temps_arret
            som_liv_vrack = (t.livraison or 0) + (t.vrack or Decimal(0))
            ensache = t.livraison * 20 if t.livraison else int()
            tx_cas = Decimal((t.casse * 100)/(ensache-t.casse)) if t.casse else Decimal('0.0')
            tx_cas = tx_cas.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            rendement = Decimal(t.livraison)/Decimal(temps_marche.total_seconds()/3600) if t.livraison else Decimal('0.0')
            rendement = rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            temps_marche_formate = get_date_formate(temps_marche)

            setattr(t, 'tx_cas', tx_cas)
            setattr(t, 'ensache', ensache)
            setattr(t, 'som_liv_vrack', som_liv_vrack)
            setattr(t, 'rendement', rendement)
            setattr(t, 'temps_marche_formate', temps_marche_formate)
            
            temps_marche_total += temps_marche if temps_marche else timedelta()
            
            livraison_total += t.livraison if t.livraison else int()
            total_ensache = livraison_total * 20
            total_vrack += Decimal(t.vrack or 0.0) if t.vrack else Decimal()
            total_sum_liv_vrack += Decimal(som_liv_vrack or 0.0) if som_liv_vrack else Decimal()
            total_casse += t.casse if t.casse else int()
            total_tx_casse = Decimal((total_casse*100)/(total_ensache - total_casse)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if total_casse > 0 else Decimal('0.0')
            total_rendement = Decimal(livraison_total/(temps_marche_total.total_seconds()/3600)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            temps_marche_total_format = get_date_formate(temps_marche_total)
            
            print(t.livraison, '===>', t.vrack, '===>', total_rendement)
            print(user, '===>', site, '===>', search_date, '===>', section)
        return{
            'search_date': search_date,
            'object_pack': pack,
            'object_pann': pann,
            'livraison_total': livraison_total,
            'total_ensache': total_ensache,
            'total_vrack': total_vrack,
            'total_casse': total_casse,
            'total_tx_casse': total_tx_casse,
            'total_rendement': total_rendement,
            'total_sum_liv_vrack': total_sum_liv_vrack,
            'temps_marche_total_format': temps_marche_total_format,
            
            'object_pack_06h_14h': pack.filter(post__post='06H-14H'),
            'object_pack_14h_22h': pack.filter(post__post='14H-22H'),
            'object_pack_22h_06h': pack.filter(post__post='22H-06H'),
            
            'object_pack_06h_18h': pack.filter(post__post='06H-18H'),
            'object_pack_18h_06h': pack.filter(post__post='18H-06H'),
            
        }
        
        
    def context_broyage(self):
        
        user = self.request.user
        profil = getattr(user, 'profil', None)
        
        if profil:
            site = profil.site
        else:
            site = None
        
        search_date = self.request.GET.get('search')
        # search_date = ""
        filter_totali_2 = Q(totaliseur__site=site)
        filter_pann = Q(broyage__site=site)
        
        if search_date:
            try:
                search_date = datetime.strptime(search_date, '%d/%m/%Y').date()
            except ValueError:
                filter_totali_2 &= Q(pk__isnull=True)
                filter_pann &= Q(pk__isnull=True)
        else:
            existe = Totaliseur_2.objects.filter(totaliseur__date=date.today(), totaliseur__site=site).exists()
            
            if existe:
                search_date = date.today()
            else:
                last_packing = Packing.objects.aggregate(Max('date'))['date__max']
                last_broyage = Totaliseur_2.objects.aggregate(Max('totaliseur__date'))['totaliseur__date__max']
                
                
                
                if last_packing and last_broyage:
                    search_date = max(last_broyage, last_packing) 
                    
                else:
                    search_date = None                  

           
        filter_totali_2 &= Q(totaliseur__date=search_date)
        filter_pann &= Q(broyage__date=search_date)
        
        t2 = Totaliseur_2.objects.filter(filter_totali_2).order_by('-totaliseur__post__post')
        object_pannes = Pannes.objects.filter(filter_pann)
        

        last_silo = t2.first()
        silo_1 = last_silo.silo_1_value if last_silo else Decimal('0.0')
        silo_2 = last_silo.silo_2_value if last_silo else Decimal('0.0')
        
        silo_1_view = silo_1 / 10
        silo_2_view = silo_2 / 10
        

        
        print('silo 1 ==>:', silo_1_view)
        print('silo 2:', silo_2_view)
        
        production_total = int()
        temps_marche_total = timedelta()
        temps_marche_total_formate = str()
        rendement_moyenne = Decimal()
        dif_compt_total = Decimal()
        conso_moyenne = Decimal()
        dif_compt_value_total = Decimal()
        for t in t2:
            temps_arret = object_pannes.filter(broyage=t.totaliseur).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = t.totaliseur.post.duree_post - temps_arret
            
            production = sum((t.dif_clinker, t.dif_gypse, t.dif_dolomite))
            temps_marche_formate = get_date_formate(temps_marche)
            rendement =Decimal(production)/Decimal(temps_marche.total_seconds()/3600) if production else Decimal('0.0')
            rendement = rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            conso = Decimal(t.dif_compt/production).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if production else Decimal('0.0') 
            dif_compt_value = Decimal(t.dif_compt/1000).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP) if t.dif_compt else Decimal('0.0')
            
            setattr(t, 'conso', conso)
            setattr(t, 'dif_compt_value', dif_compt_value)
            setattr(t, 'production', int(production))
            setattr(t, 'rendement', rendement)
            setattr(t, 'temps_marche_formate', temps_marche_formate)
             
            production_total += production
            temps_marche_total += temps_marche
            temps_marche_total_formate = get_date_formate(temps_marche_total)
            rendement_moyenne = Decimal(production_total)/Decimal(temps_marche_total.total_seconds()/3600) if production_total else Decimal('0.0')
            rendement_moyenne = rendement_moyenne.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            dif_compt_total += t.dif_compt
            conso_moyenne = Decimal(dif_compt_total/production_total).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP) if production_total else Decimal('0.0')
            dif_compt_value_total = Decimal(dif_compt_total/1000).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            
       
        
        return{
            'silo_1': silo_1,
            'silo_2': silo_2,
            'silo_1_view': silo_1_view,
            'silo_2_view': silo_2_view,
            'object_pannes': object_pannes,
            'object_broy': t2,
            'conso_moyenne': conso_moyenne,
            'rendement_moyenne': rendement_moyenne,
            'production_total': int(production_total),
            'temps_marche_total': temps_marche_total,
            'dif_compt_value_total': dif_compt_value_total,
            'temps_marche_total_formate': temps_marche_total_formate,
            
            'object_broy_06h_14h': t2.filter(totaliseur__post__post='06H-14H'),
            'object_broy_14h_22h': t2.filter(totaliseur__post__post='14H-22H'),
            'object_broy_22h_06h': t2.filter(totaliseur__post__post='22H-06H'),
            
            'object_broy_06h_18h': t2.filter(totaliseur__post__post='06H-18H'),
            'object_broy_18h_06h': t2.filter(totaliseur__post__post='18H-06H'),
           
        }

    def context_production(self):
        user = self.request.user
        profil = getattr(user, 'profil', None)
        if profil:
            site = profil.site
        else:
            site = None
            
        search_date = self.request.GET.get('search')
        filter_prod = Q(site=site)
        
        if search_date:
            try:
                search_date = datetime.strptime(search_date, '%d/%m/%Y').date()
            except ValueError:
                filter_prod &= Q(pk__isnull=True)
        else:
            existe = Production.objects.filter(date=date.today(), site=site).exists()
            
            if existe:
                search_date = date.today()
            else:
                last_production = Production.objects.aggregate(Max('date'))['date__max']
                last_broyage = Totaliseur_2.objects.aggregate(Max('totaliseur__date'))['totaliseur__date__max']
                
                if last_production and last_broyage:
                    search_date = max(last_production, last_broyage)
                else:
                    search_date = None

                    
        filter_prod &= Q(date=search_date)
        
        prod = Production.objects.filter(filter_prod)
        
        return{
            'object_production': prod,
            
            'object_production_06h_14h': prod.filter(post__post='06H-14H'),
            'object_production_14h_22h': prod.filter(post__post='14H-22H'),
            'object_production_22h_06h': prod.filter(post__post='22H-06H'),
            
            'object_production_06h_18h': prod.filter(post__post='06H-18H'),
            'object_production_18h_06h': prod.filter(post__post='18H-06H'),
        }


class packingHomeView(TemplateView):
    model = Packing
    template_name = 'packing/packing_home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        search = self.request.GET.get('search')
        
        profil = getattr(user, 'profil', None)
        if profil:
            site = profil.site
            section = profil.section
            role = profil.role
            poste = profil.poste
        else:
            site = None
            section = None
            role = None
            poste = None
            
        print(role, '====>', poste, "===>", section)
              
        filter_pack = Q(site=site)
        filter_pann = Q(packing__site=site) | Q(broyage__site=site)
            
        try:
            if search:
                search_date = datetime.strptime(search, '%d/%m/%Y').date()
            else:
                search_date = get_operational_date()
            
 
        except ValueError:
            search_date = date.today()
            
        
        
        filter_pack &= Q(date=search_date)
        filter_pann &= Q(packing__date=search_date)
        
        object_pack = Packing.objects.filter(filter_pack)
        object_pannes = Pannes.objects.filter(filter_pann).order_by('packing__post__post')
        print(object_pack.exists())
        temps_marche = timedelta()
        total_temps_arret = timedelta()
        total_temps_arret_formate = str()
        for p in object_pack:
            temps_arret = object_pannes.filter(packing=p).aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = p.post.duree_post - temps_arret
            
            # ens = (p.livraison or 0) * 20
            ens = p.livraison * 20 if p.livraison else 0
            tx_cas = Decimal((p.casse *100 )/(ens - p.casse)) if p.casse else Decimal(0.0)
            tx_cas = tx_cas.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            rend = Decimal(p.livraison)/Decimal(temps_marche.total_seconds()/3600) if p.livraison else Decimal(0.0)
            rend = rend.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            temps_marche_formate = get_date_formate(temps_marche)
            
            # total_temps_arret = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
            total_temps_arret += temps_arret
                
            total_temps_arret_formate = get_date_formate(total_temps_arret)
            
            setattr(p, 'ens', ens)
            setattr(p, 'tx_cas', tx_cas)
            setattr(p, 'rend', rend)
            setattr(p, 'temps_marche_formate', temps_marche_formate)
        
        context.update({
            'adm': 'adm',
            'role': role,
            'poste': poste,
            'search_date': search_date,
            'packing_panne': 'packing_panne',
            'section': section,
            'object_pack': object_pack,
            'object_pannes': object_pannes,
            'temps_arret_total': total_temps_arret,
            'total_temps_arret_formate': total_temps_arret_formate,
            
            'object_pack_06h_14h': object_pack.filter(post__post='06H-14H'),
            'object_pack_14h_22h': object_pack.filter(post__post='14H-22H'),
            'object_pack_22h_06h': object_pack.filter(post__post='22H-06H'),
            
            'object_pack_06h_18h': object_pack.filter(post__post='06H-18H'),
            'object_pack_18h_06h': object_pack.filter(post__post='18H-06H'),
        })
        return context
    
class packingUserView(TemplateView):
    template_name = 'packing/packing_user.html'
    
        
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
                
        user = self.kwargs.get('username')
        user = get_object_or_404(User, username=user)
        
        profil = getattr(user, 'profil', None)
        if profil:
            site = profil.site
        else:
            site = None
            
        filter_pack = Q(user=user, site=site)
           
        
        search = self.request.GET.get('search')
        existe = Packing.objects.filter(
            user=user,
            site=site,
            date__month=date.today().month,
            date__year=date.today().year
        ).exists()
        
        if search:
            keywords = [kw.strip() for kw in search.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(search, '%d/%m/%Y').date()
                    filter_pack &= Q(date=search_date)
                except ValueError:
                    if kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            search_date = datetime.strptime(str(kw_int), '%m').date()
                            filter_pack &= Q(date__month=kw_int)
                        elif 2000 <= kw_int <= date.today().year:
                            search_date = datetime.strptime(str(kw_int), '%Y').date()
                            filter_pack &= Q(date__year=kw_int)
            
        else:
            if not existe:
                month = get_operational_month()
                year = get_operational_year()
                filter_pack &= Q(date__month=month, date__year=year)
                
            else:
                month = date.today().month
                year = date.today().year
                filter_pack &= Q(date__month=month, date__year=year)
        
        object_pack = Packing.objects.filter(filter_pack)
        
        total_livraison = int(0)
        total_casse = int(0)
        total_vrack = Decimal(0.0)
        moyenne_tx_casse = Decimal(0.0)
        moyenne_rendement = Decimal(0.0)
        total_temps_arret = timedelta()
        total_temps_marche = timedelta()
        total_temps_arret_formate = str()
        total_temps_marche_formate = str()
        
        for p in object_pack:
            object_pann = Pannes.objects.filter(packing=p)
            temps_arret = object_pann.aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = p.post.duree_post - temps_arret
          
            
            ens = p.livraison * 20 if p.livraison else Decimal(0)
            tx_cas = Decimal((p.casse * 100)/(ens - p.casse)) if p.casse else Decimal(0.0)
            tx_cas = tx_cas.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            rend = Decimal(p.livraison)/Decimal(temps_marche.total_seconds()/3600) if p.livraison and temps_marche else Decimal(0.0)
            rend = rend.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            temp_arret_formate = get_date_formate(temps_arret)
            temps_marche_formate = get_date_formate(temps_marche)
            
            
            total_temps_arret += temps_arret
            if temps_marche:
                total_temps_marche += temps_marche
            else:
                total_temps_marche = timedelta()
            if p.livraison:
                total_livraison += p.livraison
            else:
                int(0)
            if p.casse:
                total_casse += p.casse
            else:
                total_casse = int(0)
            if p.vrack:
                total_vrack += Decimal(p.vrack)
            else:
                Decimal(0.0)
            
            moyenne_tx_casse = Decimal((total_casse * 100)/((total_livraison * 20) - total_casse)) if total_casse > 0 else Decimal(0.0)
            moyenne_rendement = Decimal(total_livraison)/Decimal(total_temps_marche.total_seconds()/3600) if total_livraison > 0 and total_temps_marche.total_seconds() > 0 else Decimal(0.0)
            
            moyenne_tx_casse = moyenne_tx_casse.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            moyenne_rendement = moyenne_rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            total_temps_arret_formate = get_date_formate(total_temps_arret)     
            total_temps_marche_formate = get_date_formate(total_temps_marche)
          
            
            setattr(p, 'ens', ens)
            setattr(p, 'rend', rend)
            setattr(p, 'tx_cas', tx_cas)
            setattr(p, 'temp_arret_formate', temp_arret_formate)
            setattr(p, 'temps_marche_formate', temps_marche_formate)

        
        context.update({
            'object_pack': object_pack,
            
            'total_livraison': total_livraison,
            'total_casse': total_casse,
            'total_vrack': total_vrack,
            'moyenne_tx_casse': moyenne_tx_casse,
            'moyenne_rendement': moyenne_rendement,
            'total_temps_arret': total_temps_arret,
            'total_temps_marche': total_temps_marche,
            'total_temps_arret_formate': total_temps_arret_formate,
            'total_temps_marche_formate':total_temps_marche_formate
            
        })
        return context

class packingPanneUserView(TemplateView):
    template_name =  'packing/packing_panne_admin.html'
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.kwargs.get('username')
        search = self.request.GET.get('search')
        user = get_object_or_404(User, username=user)
        profil = getattr(user, 'profil', None)
        if profil:
            section = profil.section
        else:
            section = None
            
        filter_pann = Q(packing__user=user)
        existe = Pannes.objects.filter(
            packing__user=user,
            packing__date__month = date.today().month,
            packing__date__year = date.today().year
        ).exists()
        
        if search:
            keywords = [kw.strip() for kw in search.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(search, '%d/%m/%Y').date()
                    filter_pann &= Q(packing__date=search_date)
                except ValueError:
                    if kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            search_date = datetime.strptime(str(kw_int), '%m').date()
                            filter_pann &= Q(packing__date__month=kw_int)
                        elif 2000 <= kw_int <= date.today().year:
                            search_date = datetime.strptime(str(kw_int), '%Y').date
                            filter_pann &= Q(packing__date__year=kw_int)
            
        else:
            if not existe:
                month = get_operational_month()
                year = get_operational_year()
                filter_pann &= Q(packing__date__month=month, packing__date__year=year)
                
            else:
                month = date.today().month
                year = date.today().year
                filter_pann &= Q(packing__date__month=month, packing__date__year=year)
                
        object_pannes = Pannes.objects.filter(filter_pann).order_by('-packing__post__post', '-packing__date')
        temps_arret_total = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
        total_temps_arret_formate = get_date_formate(temps_arret_total)
        
        
        context.update({
            # 'adm': 'adm',
            'total': 'total',
            'section': section,
            'object_pannes': object_pannes,
            'packing_panne': 'packing_panne',
            'temps_arret_total': temps_arret_total,
            'total_temps_arret_formate': total_temps_arret_formate
        })
        return context

class packingAdminView(TemplateView):
    template_name = 'packing/packing_admin.html'
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user = get_object_or_404(User, username=user.username)
        profil = getattr(user, 'profil', None)
        search_date = self.request.GET.get('search')
        
        if profil:
            site = profil.site
            role = profil.role
            section = profil.section
        else:
            site = None
            role = None
            section = None
            
        filter_pack = Q(site=site)
        
        existe = Packing.objects.filter(
            site=site,
            date__year=date.today().year
        ).exists()
        
        if search_date:
            keywords = [kw.strip() for kw in search_date.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(str(kw), '%d/%m/%Y').date()
                    filter_pack &= Q(date=search_date)
                except ValueError:
                    if kw.isalpha():
                        filter_pack &= Q(user__last_name__icontains=str(kw))
                        print(kw)
                    elif kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            search_date = datetime.strptime(str(kw_int), '%m').date()
                            filter_pack &= Q(date__month=kw_int)
                            print(search_date)
                            
                        elif 2000 <= kw_int <= date.today().year:
                            search_date = datetime.strptime(str(kw_int), '%Y').date()
                            filter_pack &= Q(date__year=kw_int)
            
        else:
            if not existe:
                year = get_operational_year()
                filter_pack &= Q(date__year=year)
                
            else:
                year = date.today().year
                filter_pack &= Q(date__year=year)
        
        object_pack = Packing.objects.filter(filter_pack)
        
        total_livraison = int(0)
        total_casse = int(0)
        total_vrack = Decimal(0.0)
        moyenne_tx_casse = Decimal(0.0)
        moyenne_rendement = Decimal(0.0)
        total_temps_arret = timedelta()
        total_temps_marche = timedelta()
        total_temps_arret_formate = str()
        total_temps_marche_formate = str()
        
        for p in object_pack:
            object_pann = Pannes.objects.filter(packing=p)
            temps_arret = object_pann.aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche = p.post.duree_post - temps_arret
          
            
            ens = p.livraison * 20 if p.livraison else Decimal(0)
            tx_cas = Decimal((p.casse * 100)/(ens - p.casse)) if p.casse else Decimal(0.0)
            tx_cas = tx_cas.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            rend = Decimal(p.livraison)/Decimal(temps_marche.total_seconds()/3600) if p.livraison and temps_marche else Decimal(0.0)
            rend = rend.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            temp_arret_formate = get_date_formate(temps_arret)
            temps_marche_formate = get_date_formate(temps_marche)
            
            
            total_temps_arret += temps_arret
            if temps_marche:
                total_temps_marche += temps_marche
            else:
                total_temps_marche = timedelta()
            if p.livraison:
                total_livraison += p.livraison
            else:
                int(0)
            if p.casse:
                total_casse += p.casse
                
            else:
                total_casse = int(0)
            if p.vrack:
                total_vrack += Decimal(p.vrack)
            else:
                total_vrack = Decimal('0.0')
            
            
            moyenne_tx_casse = Decimal((total_casse * 100)/((total_livraison * 20) - total_casse)) if total_casse > 0 else Decimal(0.0)
            moyenne_rendement = Decimal(total_livraison)/Decimal(total_temps_marche.total_seconds()/3600) if total_livraison > 0 and total_temps_marche.total_seconds() > 0 else Decimal(0.0)
            
            moyenne_tx_casse = moyenne_tx_casse.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            moyenne_rendement = moyenne_rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            total_temps_arret_formate = get_date_formate(total_temps_arret)     
            total_temps_marche_formate = get_date_formate(total_temps_marche)
        
            setattr(p, 'ens', ens)
            setattr(p, 'rend', rend)
            setattr(p, 'tx_cas', tx_cas)
            setattr(p, 'temp_arret_formate', temp_arret_formate)
            setattr(p, 'temps_marche_formate', temps_marche_formate)

            print('total_temps_marche:', total_temps_marche)
        context.update({
            'role': role,
            'section': section,
            'search_date': search_date,
            'object_pack': object_pack,
            
            'total_livraison': total_livraison,
            'total_casse': total_casse,
            'total_vrack': total_vrack,
            'moyenne_tx_casse': moyenne_tx_casse,
            'moyenne_rendement': moyenne_rendement,
            'total_temps_arret': total_temps_arret,
            'total_temps_marche': total_temps_marche,
            'total_temps_arret_formate': total_temps_arret_formate,
            'total_temps_marche_formate':total_temps_marche_formate
            
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
            template = get_template('packing/packing_admin_pdf.html')
            html_string = template.render(context)
            pdf_file = HTML(string=html_string,
                            base_url=request.build_absolute_uri()).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response

        return self.render_to_response(context)

class packingPanneAdminView(TemplateView):
    template_name =  'packing/packing_panne_admin.html'
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user = get_object_or_404(User, username=user)
        
        search = self.request.GET.get('search')

        profil = getattr(user, 'profil', None)
        if profil:
            site = profil.site
            role = profil.role
            section = profil.section
        else:
            site = None
            role = None
            section = None
            
        filter_pann = Q(packing__site=site)
        
        existe = Pannes.objects.filter(
            packing__site = site,
            packing__date__year = date.today().year
        ).exists()
        
        if search:
            keywords = [kw.strip() for kw in search.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(kw, '%d/%m/%Y').date()
                    filter_pann &= Q(packing__date=search_date)
                except ValueError:
                    if kw.isalpha():
                        filter_pann &= Q(packing__user__last_name__icontains=str(kw))
                        
                    elif kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            search_date = datetime.strptime(str(kw_int), '%m').date()
                            filter_pann &= Q(packing__date__month=kw_int)
                            
                        elif 2000 <= kw_int <= date.today().year:
                            search_date = kw_int
                            # search_date = datetime.strptime(str(kw_int), '%Y').date
                            filter_pann &= Q(packing__date__year=kw_int)
                            
            
        else:
            if not existe:
                year = get_operational_year()
                filter_pann &= Q(packing__date__year=year)
                
            else:
                year = date.today().year
                filter_pann &= Q(packing__date__year=year)
                
        object_pannes = Pannes.objects.filter(filter_pann).order_by('-packing__date')
        temps_arret_total = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
        total_temps_arret_formate = get_date_formate(temps_arret_total)
        
        print('temps_arret_total:', temps_arret_total)

        context.update({
            # 'adm': 'adm',
            'total': 'total',
            'role': role,
            'section': section,
            'temps_arret_total': temps_arret_total,
            'object_pannes': object_pannes,
            'packing_panne': 'packing_panne',
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
            template = get_template('packing/packing_panne_admin_pdf.html')
            html_string = template.render(context)
            pdf_file = HTML(string=html_string,
                            base_url=request.build_absolute_uri()).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response

        return self.render_to_response(context)

class ajout_Packing(CreateView):
    model = Packing
    form_class = PackingForm
    template_name = 'packing/formulaire.html'
    success_url = reverse_lazy('packing:packing_home')
    
    def form_valid(self, form):
        user = self.request.user
        profil = getattr(user, 'profil', None)
        if profil:
            site = profil.site
        else:
            site = None
            
        form.instance.user = user
        form.instance.site = site
        post = form.cleaned_data.get('post')
        date = form.cleaned_data.get('date')
        
        user_post_existe = Packing.objects.filter(
            post = post,
            date = date,
        ).exists()
        
        
        existe = Packing.objects.filter(
            site = site,
            post = post,
            date = date,
        ).exists()
        
        if existe:
            messages.warning(
                self.request, "Un objet pour ce poste existe déjà aujourd’hui.")
            return redirect('packing:ajout_packing')
        
        elif user_post_existe:
            messages.warning(
                self.request, "Vous avez déjà enregistré un ensachage pour ce poste aujourd’hui.")
            return redirect('packing:ajout_packing')
        
        else:
            messages.success(self.request, "✅ Ensachage enregistré avec succès.")
            
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["ajout_packing"] = 'ajout_packing'
        return context
       
class ajout_Packing_Pannes(CreateView):
    model = Pannes
    form_class = PanneForm
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    template_name = 'packing/formulaire.html'
    
    def form_valid(self, form):
        slug = self.kwargs.get('slug')
        pack = get_object_or_404(Packing, slug=slug)
        form.instance.packing = pack
        
        return super().form_valid(form)
    
    def get_success_url(self) -> str:
        slug = self.kwargs.get('slug')
        base_url = reverse_lazy('packing:ajout_packing_panne', kwargs={'slug': slug})
        return f'{base_url}'
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug')
        pack = get_object_or_404(Packing, slug=slug)
        object_pannes = Pannes.objects.filter(packing=pack)
        temps_arret_total = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
        total_temps_arret_formate = get_date_formate(temps_arret_total)
        context.update({
            'packing_panne': 'packing_panne',
            'object_pannes': object_pannes,
            'temps_arret_total': temps_arret_total,
            'total_temps_arret_formate': total_temps_arret_formate,
        })
        return context

class update_packing(UpdateView):
    model = Packing
    form_class = PackingForm
    template_name = 'packing/formulaire.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('packing:packing_home')
    
    
    def form_valid(self, form):
        self.object = self.get_object()  # ✅ important : récupérer l’objet avant tout

        user = self.request.user
        profil = getattr(user, 'profil', None)
        site = profil.site if profil else None

        form.instance.user = user
        form.instance.site = site
        post = form.cleaned_data.get('post')
        date = form.cleaned_data.get('date')

        existe = Packing.objects.filter(
            site=site,
            post=post,
            date=date,
        ).exclude(pk=self.object.pk).exists()  # ✅ exclusion de l’objet actuel

        if existe:
            messages.warning(
                self.request,
                "Un objet pour ce poste existe déjà aujourd’hui."
            )
            return redirect(self.request.path)  # ✅ renvoie sur la même page d’édition

        messages.success(self.request, "✅ Ensachage mis à jour avec succès.")
        return super().form_valid(form)


    
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["update_packing"] = 'update_packing'
        return context  
    
class update_packing_panne(UpdateView):
    model = Pannes
    form_class = PanneForm
    template_name = 'packing/formulaire.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('packing:update_packing_panne')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug')
        object = get_object_or_404(Pannes, slug=slug)
        
        object_pannes = Pannes.objects.filter(slug=object.slug)
        
        temps_arret_total = object_pannes.aggregate(total=Sum('duree'))['total'] or timedelta()
        total_temps_arret_formate = get_date_formate(temps_arret_total)
        context.update({
            'packing_panne': 'packing_panne',
            'object_pannes': object_pannes,
            'total_temps_arret_formate': total_temps_arret_formate,
            'temps_arret_total': temps_arret_total,
        })
        
        return context
            
    def get_success_url(self) -> str:
        slug = self.kwargs.get('slug')
        base_url = reverse_lazy('packing:update_packing_panne', kwargs = {'slug': slug})
        return f'{base_url}'

class dashboard(TemplateView):
    model = Packing
    template_name = 'packing/dashboard.html'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
                
        user = self.request.user
        
        profil = getattr(user, 'profil', None)
        if profil:
            site = profil.site
        else:
            site = None
            
        filter_pack = Q(site=site)
        print(site)
           
        
        search = self.request.GET.get('search')
        existe = Packing.objects.filter(
            site=site,
            date__month=date.today().month,
            date__year=date.today().year
        ).exists()
        
        if search:
            keywords = [kw.strip() for kw in search.split(',') if kw.strip()]
            for kw in keywords:
                try:
                    search_date = datetime.strptime(search, '%d/%m/%Y').date()
                    filter_pack &= Q(date=search_date)
                except ValueError:
                    if kw.isdigit():
                        kw_int = int(kw)
                        if 1 <= kw_int <= 12:
                            search_date = datetime.strptime(str(kw_int), '%m').date()
                            filter_pack &= Q(date__month=kw_int)
                        elif 2000 <= kw_int <= date.today().year:
                            search_date = datetime.strptime(str(kw_int), '%Y').date()
                            filter_pack &= Q(date__year=kw_int)
            
        else:
            if not existe:
                month = get_operational_month()
                year = get_operational_year()
                filter_pack &= Q(date__year=year)
                print('non')
                
            else:
                month = date.today().month
                year = date.today().year
                filter_pack &= Q(date__year=year)
                print('oui')
        
        object_pack = Packing.objects.filter(filter_pack)
        
        total_livraison = int(0)
        total_casse = int(0)
        total_vrack = Decimal(0.0)
        moyenne_tx_casse = Decimal(0.0)
        moyenne_rendement = Decimal(0.0)
        total_temps_arret = timedelta()
        total_temps_marche = timedelta()
        total_temps_arret_formate = str()
        total_temps_marche_formate = str()
        labels, livraison, casse, tx_casse, rendement, temp_arret = [], [], [], [], [], []
        
        for p in object_pack:
            object_pann = Pannes.objects.filter(packing=p)
            temps_arret_value = object_pann.aggregate(total=Sum('duree'))['total'] or timedelta()
            temps_marche_value = p.post.duree_post - temps_arret_value
          
            
            ens = p.livraison * 20 if p.livraison else Decimal(0)
            tx_cas = Decimal((p.casse * 100)/(ens - p.casse)) if p.casse else Decimal(0.0)
            tx_cas = tx_cas.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            rend = Decimal(p.livraison)/Decimal(temps_marche_value.total_seconds()/3600) if p.livraison and temps_marche_value else Decimal(0.0)
            rend = rend.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # temp_arret_formate = get_date_formate(temps_arret)
            # temps_marche_formate = get_date_formate(temps_marche)
            
            temps_arret = Decimal(temps_arret_value.total_seconds()/3600).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            temps_marche = Decimal(temps_marche_value.total_seconds()/3600).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            
            total_temps_arret += temps_arret_value
            if temps_marche:
                total_temps_marche += temps_marche_value
            else:
                total_temps_marche = timedelta()
            if p.livraison:
                total_livraison += p.livraison
            else:
                int(0)
            if p.casse:
                total_casse += p.casse
            else:
                total_casse = int(0)
            if p.vrack:
                total_vrack += Decimal(p.vrack)
            else:
                Decimal(0.0)
            
            moyenne_tx_casse = Decimal((total_casse * 100)/((total_livraison * 20) - total_casse))
            moyenne_rendement = Decimal(total_livraison)/Decimal(total_temps_marche.total_seconds()/3600)
            
            moyenne_tx_casse = moyenne_tx_casse.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            moyenne_rendement = moyenne_rendement.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            total_temps_arret_formate = get_date_formate(total_temps_arret)     
            total_temps_marche_formate = get_date_formate(total_temps_marche)
          
            
            # Remplir les listes
            labels.append(p.date.strftime("%d/%m/%Y"))
            if p.livraison and p.casse:
                livraison.append(float(p.livraison))
                casse.append(float(p.casse))
                tx_casse.append(float(tx_cas))
                rendement.append(float(rend))
                temp_arret.append(float(temps_arret))
            
        context.update({
            'packing': 'packing',
            "object_pack": object_pack,
            "labels": json.dumps(labels),
            "livraison": json.dumps(livraison),
            "casse": json.dumps(casse),
            "tx_casse": json.dumps(tx_casse),
            "rendement": json.dumps(rendement),
            "temp_arret": json.dumps(temp_arret),

            "total_livraison": total_livraison,
            "total_casse": total_casse,
            "moyenne_tx_casse": moyenne_tx_casse.quantize(Decimal('.01'), rounding=ROUND_HALF_UP),
            "moyenne_rendement": moyenne_rendement.quantize(Decimal('.01'), rounding=ROUND_HALF_UP),
        })
        return context








