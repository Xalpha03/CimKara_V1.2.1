from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, DetailView
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from .forms import UserProfilForm
from django.contrib.auth import logout, login
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from django.shortcuts import redirect


from django.contrib.auth import get_user_model

User = get_user_model()

class UserCreate(CreateView):
    model = User
    form_class = UserProfilForm
    template_name = "account/register.html"

    def form_valid(self, form):
        profil = form.save()  # Le formulaire retourne un objet Profil, pas User
        user = profil.user  # Récupérer le User depuis le Profil
        self.request.session["created_user_id"] = user.pk
        return redirect("account:accueil", pk=user.pk)


class AccueilView(TemplateView): 
    template_name = "account/accueil.html" 

    def get_context_data(self, **kwargs): 
        context = super().get_context_data(**kwargs) 
        pk = self.kwargs.get("pk")
        user = get_object_or_404(User, pk=pk)
        context["created_user"] = user
        return context


def auto_login(request): 
    user_id = request.session.get("created_user_id") 
    if user_id: 
        try:
            user = User.objects.get(pk=user_id) 
            login(request, user)
            del request.session["created_user_id"]
            return redirect("home_page")
        except User.DoesNotExist:
            # Nettoyer la session si l'utilisateur n'existe plus
            del request.session["created_user_id"]
            return redirect("account:login")
    return redirect("account:login")




    
    
class UserLoginView(LoginView):
    template_name = 'account/login.html'
    redirect_authenticated_user = True  # évite de reconnecter un utilisateur déjà connecté
    def get_success_url(self):
        user=self.request.user
        
        profil = getattr(user, 'profil', None)
        if profil:
            section = profil.poste
        print(section)
        
        if not user.is_authenticated:
            return reverse_lazy('account:login')
        
        if not hasattr(user, 'profil'):
            messages.warning(self.request, "Votre compte n'a pas encore de profil associé.")
            return reverse_lazy('home_view')
        
        messages.success(self.request, "Vous avez été connecté.")
        
        if section == 'broyage':
            return reverse_lazy('broyage:broyage_home')  # ou dashboard selon le rôle
        elif section == 'packing':
            return reverse_lazy('packing:packing_home')
        else:
            return reverse_lazy('home_page')
    
    
def custom_logout(request):
    logout(request)
    messages.success(request, "Vous avez été déconnecté.")
    return redirect('account:login')




