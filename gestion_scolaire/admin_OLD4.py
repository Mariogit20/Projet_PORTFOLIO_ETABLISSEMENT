from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Dren, Cisco, Zap, Fokontany, Etablissement, LienPortfolio, Presence, UserProfile

@admin.register(Dren)
class DrenAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom'); search_fields = ('nom',); ordering = ('id',)

@admin.register(Cisco)
class CiscoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'dren'); list_filter = ('dren',); search_fields = ('nom',); autocomplete_fields = ['dren']; ordering = ('id',)

@admin.register(Zap)
class ZapAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'cisco'); list_filter = ('cisco__dren',); search_fields = ('nom',); autocomplete_fields = ['cisco']; ordering = ('id',)

@admin.register(Fokontany)
class FokontanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'zap'); list_filter = ('zap__cisco__dren',); search_fields = ('nom',); autocomplete_fields = ['zap']; ordering = ('id',)

@admin.register(Etablissement)
class EtablissementAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'fokontany_info'); list_filter = ('fokontany__zap__cisco__dren',); search_fields = ('nom',); autocomplete_fields = ['fokontany']; ordering = ('id',)
    def fokontany_info(self, obj): return f"{obj.fokontany.nom} (ZAP: {obj.fokontany.zap.nom})"
    fokontany_info.short_description = 'Fokontany'

class PresenceInline(admin.TabularInline):
    model = Presence; extra = 1; autocomplete_fields = ['etablissement']

@admin.register(LienPortfolio)
class LienPortfolioAdmin(admin.ModelAdmin):
    list_display = ('cin', 'nom_prenom', 'lien'); search_fields = ('cin', 'nom_prenom'); inlines = [PresenceInline]

@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ('personne', 'etablissement', 'date_debut', 'date_fin'); list_filter = ('etablissement', 'date_debut'); search_fields = ('personne__nom_prenom', 'personne__cin', 'etablissement__nom'); autocomplete_fields = ['personne', 'etablissement']

class UserProfileInline(admin.StackedInline):
    model = UserProfile; can_delete = False; verbose_name_plural = 'Profil Utilisateur (Rôles & Autorisations)'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, )

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.site_header = "Administration - Gestion Scolaire"