from django.shortcuts import render

from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.generic.edit import FormView
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .forms import RegistrationForm, LoginForm
from django.views.generic import DetailView, ListView

from profiles.models import Follow
from profiles.forms import FollowForm

from profiles.models import UserProfile
from django.views.generic.edit import UpdateView
from posts.models import Post

class HomeView(TemplateView):
    template_name = "general/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Si el usuario está logueado:
        if self.request.user.is_authenticated:
            # Obtenemos los posts de los usuarios que seguimos
            seguidos = Follow.objects.filter(follower=self.request.user.profile).values_list('following__user', flat=True)
            # Nos traemos los posts de los usuarios que seguimos
            last_posts = Post.objects.filter(user__profile__user__in=seguidos)

        else:
            last_posts = Post.objects.all().order_by('-created_at')[:10]
        context['last_posts'] = last_posts

        return context



class LoginView(FormView):
    template_name = "general/login.html"
    form_class = LoginForm

    def form_valid(self, form):
        usuario = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(username=usuario, password=password)

        if user is not None:
            login(self.request, user)
            messages.add_message(self.request, messages.SUCCESS, f'Bienvenido de nuevo {user.username}')
            return HttpResponseRedirect(reverse('home'))

        else:
            messages.add_message(
                self.request, messages.ERROR, 'Usuario no válido o contraseña no válida')
            return super(LoginView, self).form_invalid(form)


class RegisterView(CreateView):
    template_name = "general/register.html"
    model = User
    success_url = reverse_lazy('login')
    form_class = RegistrationForm

    def form_valid(self, form):
        messages.add_message(self.request, messages.SUCCESS, "Usuario creado correctamente.")
        return super(RegisterView, self).form_valid(form)


class LegalView(TemplateView):
    template_name = "general/legal.html"


class ContactView(TemplateView):
    template_name = "general/contact.html"

class ProfileDetailView(DetailView, FormView):
    model = UserProfile
    template_name = "general/profile_detail.html"
    context_object_name = "profile"
    form_class = FollowForm

    def get_object(self):
        # Sobreescribe `get_object` para asegurar que `self.object` esté disponible en `POST` y `GET`
        if not hasattr(self, 'object'):
            self.object = super().get_object()
        return self.object

    def get_initial(self):
        initial = super().get_initial()
        initial['profile_pk'] = self.get_object().pk
        return initial
    
    def form_valid(self, form):
        self.object = self.get_object()  # Carga el objeto para la solicitud POST
        profile_pk = form.cleaned_data.get('profile_pk')
        following = UserProfile.objects.get(pk=profile_pk)

        if Follow.objects.filter(
                follower=self.request.user.profile,
                following=following
            ).count():
                Follow.objects.filter(
                    follower=self.request.user.profile,
                    following=following
                ).delete()
                messages.add_message(self.request, messages.SUCCESS, f"Se ha dejado de seguir a {following.user.username}")
        else:
                Follow.objects.get_or_create(
                follower=self.request.user.profile,
                following=following
                )
                messages.add_message(self.request, messages.SUCCESS, f"Se empieza a seguir a {following.user.username}")
        return super().form_valid(form)


    def get_success_url(self):
        return reverse('profile_detail', args=[self.get_object().pk])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Comprobamos si seguimos al usuario
        following = Follow.objects.filter(follower=self.request.user.profile, following=self.get_object()).exists()
        context['following'] = following
        return context

@method_decorator(login_required, name='dispatch')
class ProfileUpdateView(UpdateView):
    model = UserProfile
    template_name = "general/profile_update.html"
    context_object_name = "profile"
    fields = ['profile_picture', 'bio', 'birth_date']

    def dispatch(self, request, *args, **kwargs):
        user_profile = self.get_object()
        if user_profile.user != self.request.user:
            return HttpResponseRedirect(reverse('home'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.add_message(self.request, messages.SUCCESS, "Perfil editado correctamente.")
        return super(ProfileUpdateView, self).form_valid(form)
    
    def get_success_url(self):
        return reverse('profile_detail', args=[self.object.pk])
    
class ProfileListView(ListView):
    model = UserProfile
    template_name = "general/profile_list.html"
    context_object_name = "profiles"

    def get_queryset(self):
        if self.request.user.is_authenticated:
            queryset = UserProfile.objects.exclude(user=self.request.user).order_by('user__username')
        else:
            queryset = UserProfile.objects.all().order_by('user__username')
        print(queryset)  # Verifica qué perfiles se están obteniendo
        return queryset


@login_required
def logout_view(request):
    logout(request)
    messages.add_message(request, messages.INFO, "Se ha cerrado sesión correctamente.")
    return HttpResponseRedirect(reverse('home'))