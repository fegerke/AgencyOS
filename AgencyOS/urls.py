from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    
    # Rota de Logout customizada
    path('logout/', auth_views.LogoutView.as_view(template_name='core/logout.html'), name='logout'),
    
    path('', home, name='home'),
    path('', include('core.urls')),
]