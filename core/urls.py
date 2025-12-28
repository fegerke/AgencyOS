from django.contrib import admin
from django.urls import path
from posts.views import home  # Importando a view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
]
