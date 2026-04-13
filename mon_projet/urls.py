from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User

# On importe les vues de votre application gestion_scolaire
from gestion_scolaire import views 

def custom_login(request, **kwargs):
    if not User.objects.exists():
        User.objects.create_superuser('admin', 'admin@ecole.mg', 'admin123')
    return auth_views.LoginView.as_view(template_name='login.html')(request, **kwargs)

urlpatterns = [
    # === L'ACCÈS À L'ADMINISTRATION DJANGO ===
    path('admin/', admin.site.urls),

    # === SÉCURITÉ ET CONNEXION ===
    path('login/', custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # === UTILISATEURS ===
    path('utilisateurs/', views.manage_users, name='manage_users'),
    path('utilisateurs/<int:id>/', views.manage_users, name='manage_users'),
    path('utilisateurs/supprimer/<int:id>/', views.delete_user, name='delete_user'),

    # === RECHERCHE ET ACCUEIL ===
    path('', views.index_crud, name='index'),
    path('api/autocomplete/', views.search_autocomplete, name='autocomplete'),
    
    # === GÉOGRAPHIE ===
    path('dren/', views.manage_dren, name='manage_dren'),
    path('dren/<int:id>/', views.manage_dren, name='manage_dren'),
    path('dren/supprimer/<int:id>/', views.delete_dren, name='delete_dren'),

    path('cisco/', views.manage_cisco, name='manage_cisco'),
    path('cisco/<int:id>/', views.manage_cisco, name='manage_cisco'),
    path('cisco/supprimer/<int:id>/', views.delete_cisco, name='delete_cisco'),

    path('zap/', views.manage_zap, name='manage_zap'),
    path('zap/<int:id>/', views.manage_zap, name='manage_zap'),
    path('zap/supprimer/<int:id>/', views.delete_zap, name='delete_zap'),

    path('fokontany/', views.manage_fokontany, name='manage_fokontany'),
    path('fokontany/<int:id>/', views.manage_fokontany, name='manage_fokontany'),
    path('fokontany/supprimer/<int:id>/', views.delete_fokontany, name='delete_fokontany'),

    path('etablissement/', views.manage_etablissement, name='manage_etablissement'),
    path('etablissement/<int:id>/', views.manage_etablissement, name='manage_etablissement'),
    path('etablissement/supprimer/<int:id>/', views.delete_etablissement, name='delete_etablissement'),

    # === RESSOURCES HUMAINES ===
    path('portfolio/', views.manage_portfolio, name='manage_portfolio'),
    path('portfolio/<int:id>/', views.manage_portfolio, name='manage_portfolio'),
    path('portfolio/supprimer/<int:id>/', views.delete_portfolio, name='delete_portfolio'),

    path('presence/', views.manage_presence, name='manage_presence'),
    path('presence/<int:id>/', views.manage_presence, name='manage_presence'),
    path('presence/supprimer/<int:id>/', views.delete_presence, name='delete_presence'),
    
    # === SAUVEGARDE ET RESTAURATION ===
    path('export-json/', views.export_data, name='export_data'),
    path('import-json/', views.import_data, name='import_data'),
]