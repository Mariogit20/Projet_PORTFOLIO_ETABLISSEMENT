import json
import Levenshtein
from datetime import datetime
from itertools import chain
from django.db.models.functions import Length
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Dren, Cisco, Zap, Fokontany, Etablissement, LienPortfolio, Presence

def clean_text(text): return " ".join(text.split()) if text else None

def has_perm(user, action):
    if user.is_superuser: return True
    try: profile = user.profile
    except: return False
    if action == 'add': return profile.can_add
    if action == 'edit': return profile.can_edit
    if action == 'delete': return profile.can_delete
    return False

def filter_queryset_by_user(queryset, user, entity_type):
    """ Filtre les requêtes de la Base de Données selon la restriction de l'utilisateur """
    if user.is_superuser or not hasattr(user, 'profile'): return queryset
    p = user.profile
    d_id, c_id, z_id, f_id, e_id = p.dren_assignee_id, p.cisco_assignee_id, p.zap_assignee_id, p.fokontany_assignee_id, p.etablissement_assignee_id
    
    if entity_type == 'dren':
        if e_id: return queryset.filter(id=p.etablissement_assignee.fokontany.zap.cisco.dren_id)
        if f_id: return queryset.filter(id=p.fokontany_assignee.zap.cisco.dren_id)
        if z_id: return queryset.filter(id=p.zap_assignee.cisco.dren_id)
        if c_id: return queryset.filter(id=p.cisco_assignee.dren_id)
        if d_id: return queryset.filter(id=d_id)
        
    elif entity_type == 'cisco':
        if e_id: return queryset.filter(id=p.etablissement_assignee.fokontany.zap.cisco_id)
        if f_id: return queryset.filter(id=p.fokontany_assignee.zap.cisco_id)
        if z_id: return queryset.filter(id=p.zap_assignee.cisco_id)
        if c_id: return queryset.filter(id=c_id)
        if d_id: return queryset.filter(dren_id=d_id)
        
    elif entity_type == 'zap':
        if e_id: return queryset.filter(id=p.etablissement_assignee.fokontany.zap_id)
        if f_id: return queryset.filter(id=p.fokontany_assignee.zap_id)
        if z_id: return queryset.filter(id=z_id)
        if c_id: return queryset.filter(cisco_id=c_id)
        if d_id: return queryset.filter(cisco__dren_id=d_id)
        
    elif entity_type == 'fokontany':
        if e_id: return queryset.filter(id=p.etablissement_assignee.fokontany_id)
        if f_id: return queryset.filter(id=f_id)
        if z_id: return queryset.filter(zap_id=z_id)
        if c_id: return queryset.filter(zap__cisco_id=c_id)
        if d_id: return queryset.filter(zap__cisco__dren_id=d_id)
        
    elif entity_type == 'etablissement':
        if e_id: return queryset.filter(id=e_id)
        if f_id: return queryset.filter(fokontany_id=f_id)
        if z_id: return queryset.filter(fokontany__zap_id=z_id)
        if c_id: return queryset.filter(fokontany__zap__cisco_id=c_id)
        if d_id: return queryset.filter(fokontany__zap__cisco__dren_id=d_id)
        
    elif entity_type == 'presence':
        if e_id: return queryset.filter(etablissement_id=e_id)
        if f_id: return queryset.filter(etablissement__fokontany_id=f_id)
        if z_id: return queryset.filter(etablissement__fokontany__zap_id=z_id)
        if c_id: return queryset.filter(etablissement__fokontany__zap__cisco_id=c_id)
        if d_id: return queryset.filter(etablissement__fokontany__zap__cisco__dren_id=d_id)
        
    return queryset

@login_required
def manage_users(request, id=None):
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé. Réservé à l'Admin National."); return redirect('index')
    
    instance = get_object_or_404(User, id=id) if id else None
    if request.method == 'POST':
        username, password, role = clean_text(request.POST.get('username')), request.POST.get('password'), request.POST.get('role', 'INVITE')
        is_superuser, can_add, can_edit, can_delete = request.POST.get('is_superuser') == 'on', request.POST.get('can_add') == 'on', request.POST.get('can_edit') == 'on', request.POST.get('can_delete') == 'on'
        
        if username:
            if User.objects.filter(username__iexact=username).exclude(id=instance.id if instance else None).exists():
                messages.error(request, f"Le login '{username}' existe déjà.")
            else:
                if instance:
                    instance.username, instance.is_superuser, instance.is_staff = username, is_superuser, is_superuser
                    if password: instance.set_password(password)
                    instance.save(); user_to_update = instance
                else:
                    if not password: messages.error(request, "Mot de passe obligatoire."); return redirect('manage_users')
                    user_to_update = User.objects.create_user(username=username, password=password)
                    user_to_update.is_superuser, user_to_update.is_staff = is_superuser, is_superuser; user_to_update.save()
                
                profile = user_to_update.profile
                profile.role, profile.can_add, profile.can_edit, profile.can_delete = role, (can_add if not is_superuser else True), (can_edit if not is_superuser else True), (can_delete if not is_superuser else True)
                profile.dren_assignee_id = request.POST.get('dren_assignee') or None
                profile.cisco_assignee_id = request.POST.get('cisco_assignee') or None
                profile.zap_assignee_id = request.POST.get('zap_assignee') or None
                profile.fokontany_assignee_id = request.POST.get('fokontany_assignee') or None
                profile.etablissement_assignee_id = request.POST.get('etablissement_assignee') or None
                profile.save()
                messages.success(request, "Utilisateur et permissions enregistrés."); return redirect('manage_users')
                
    return render(request, 'manage_users.html', {'utilisateurs': User.objects.all().select_related('profile').order_by('-id'), 'edit_obj': instance})

@login_required
def delete_user(request, id):
    if not request.user.is_superuser: return redirect('index')
    if request.method == 'POST':
        user = get_object_or_404(User, id=id)
        if user == request.user: messages.error(request, "Impossible de supprimer votre propre compte.")
        else: user.delete(); messages.success(request, "Utilisateur supprimé.")
    return redirect('manage_users')

@login_required
def index_crud(request): return render(request, 'index.html')

@login_required
def search_autocomplete(request):
    term, entity_type, parent_id = request.GET.get('term', ''), request.GET.get('type', ''), request.GET.get('parent_id', '')
    
    if entity_type == 'dren': queryset = Dren.objects.all()
    elif entity_type == 'cisco' and parent_id: queryset = Cisco.objects.filter(dren_id=parent_id)
    elif entity_type == 'zap' and parent_id: queryset = Zap.objects.filter(cisco_id=parent_id)
    elif entity_type == 'fokontany' and parent_id: queryset = Fokontany.objects.filter(zap_id=parent_id)
    elif entity_type == 'etablissement' and parent_id: queryset = Etablissement.objects.filter(fokontany_id=parent_id)
    elif entity_type == 'etablissement_global': queryset = Etablissement.objects.select_related('fokontany__zap__cisco__dren').all()
    else: return JsonResponse([], safe=False)

    queryset = filter_queryset_by_user(queryset, request.user, 'etablissement' if 'global' in entity_type else entity_type)

    term = clean_text(term)
    if not term: return JsonResponse([], safe=False)
    term_length = len(term)
    threshold = max(2, term_length // 2)
    queryset = queryset.annotate(nom_len=Length('nom')).filter(nom_len__gte=term_length - threshold, nom_len__lte=term_length + threshold + 5)
    
    results = []
    for obj in queryset:
        distance = Levenshtein.distance(term.lower(), obj.nom.lower())
        if term.lower() in obj.nom.lower() or distance <= threshold:
            nom_complet = f"{obj.nom} (DREN: {obj.fokontany.zap.cisco.dren.nom})" if entity_type == 'etablissement_global' else obj.nom
            results.append({'id': obj.id, 'nom': nom_complet, 'distance': distance})
    results.sort(key=lambda x: x['distance'])
    return JsonResponse([{'id': r['id'], 'nom': r['nom']} for r in results[:10]], safe=False)

@login_required
def manage_dren(request, id=None):
    instance = get_object_or_404(Dren, id=id) if id else None
    if request.method == 'POST':
        if not has_perm(request.user, 'edit' if instance else 'add'): messages.error(request, "Accès refusé."); return redirect('manage_dren')
        
        allowed = filter_queryset_by_user(Dren.objects.all(), request.user, 'dren')
        if (instance and not allowed.filter(id=instance.id).exists()) or (not instance and not request.user.is_superuser):
            messages.error(request, "Alerte : Vous n'avez pas les droits pour cette DREN."); return redirect('manage_dren')

        nom = clean_text(request.POST.get('nom_dren'))
        if nom:
            if Dren.objects.filter(nom__iexact=nom).exclude(id=instance.id if instance else None).exists(): messages.error(request, f"La DREN '{nom}' existe déjà.")
            else:
                if instance: instance.nom = nom; instance.save()
                else: Dren.objects.create(nom=nom)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_dren')
                
    drens = filter_queryset_by_user(Dren.objects.all(), request.user, 'dren').order_by('nom')
    return render(request, 'manage_dren.html', {'drens': drens, 'edit_obj': instance})

@login_required
def delete_dren(request, id):
    if not has_perm(request.user, 'delete'): return redirect('manage_dren')
    if filter_queryset_by_user(Dren.objects.all(), request.user, 'dren').filter(id=id).exists() and request.method == 'POST':
        get_object_or_404(Dren, id=id).delete()
    else: messages.error(request, "Interdit.")
    return redirect('manage_dren')

@login_required
def manage_cisco(request, id=None):
    instance = get_object_or_404(Cisco, id=id) if id else None
    if request.method == 'POST':
        if not has_perm(request.user, 'edit' if instance else 'add'): messages.error(request, "Accès refusé."); return redirect('manage_cisco')
        nom, dren_id = clean_text(request.POST.get('nom_cisco')), request.POST.get('dren_id')
        if nom and dren_id:
            if not filter_queryset_by_user(Dren.objects.all(), request.user, 'dren').filter(id=dren_id).exists() or (instance and not filter_queryset_by_user(Cisco.objects.all(), request.user, 'cisco').filter(id=instance.id).exists()):
                messages.error(request, "Alerte : Juridiction dépassée."); return redirect('manage_cisco')
            if Cisco.objects.filter(nom__iexact=nom, dren_id=dren_id).exclude(id=instance.id if instance else None).exists(): messages.error(request, "CISCO existante.")
            else:
                if instance: instance.nom, instance.dren_id = nom, dren_id; instance.save()
                else: Cisco.objects.create(nom=nom, dren_id=dren_id)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_cisco')
                
    ciscos = filter_queryset_by_user(Cisco.objects.select_related('dren'), request.user, 'cisco').order_by('nom')
    return render(request, 'manage_cisco.html', {'ciscos': ciscos, 'edit_obj': instance})

@login_required
def delete_cisco(request, id):
    if not has_perm(request.user, 'delete'): return redirect('manage_cisco')
    if filter_queryset_by_user(Cisco.objects.all(), request.user, 'cisco').filter(id=id).exists() and request.method == 'POST':
        get_object_or_404(Cisco, id=id).delete()
    else: messages.error(request, "Interdit.")
    return redirect('manage_cisco')

@login_required
def manage_zap(request, id=None):
    instance = get_object_or_404(Zap, id=id) if id else None
    if request.method == 'POST':
        if not has_perm(request.user, 'edit' if instance else 'add'): messages.error(request, "Accès refusé."); return redirect('manage_zap')
        nom, cisco_id = clean_text(request.POST.get('nom_zap')), request.POST.get('cisco_id')
        if nom and cisco_id:
            if not filter_queryset_by_user(Cisco.objects.all(), request.user, 'cisco').filter(id=cisco_id).exists() or (instance and not filter_queryset_by_user(Zap.objects.all(), request.user, 'zap').filter(id=instance.id).exists()):
                messages.error(request, "Alerte : Juridiction dépassée."); return redirect('manage_zap')
            if Zap.objects.filter(nom__iexact=nom, cisco_id=cisco_id).exclude(id=instance.id if instance else None).exists(): messages.error(request, "ZAP existante.")
            else:
                if instance: instance.nom, instance.cisco_id = nom, cisco_id; instance.save()
                else: Zap.objects.create(nom=nom, cisco_id=cisco_id)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_zap')
                
    zaps = filter_queryset_by_user(Zap.objects.select_related('cisco__dren'), request.user, 'zap').order_by('nom')
    return render(request, 'manage_zap.html', {'zaps': zaps, 'edit_obj': instance})

@login_required
def delete_zap(request, id):
    if not has_perm(request.user, 'delete'): return redirect('manage_zap')
    if filter_queryset_by_user(Zap.objects.all(), request.user, 'zap').filter(id=id).exists() and request.method == 'POST': get_object_or_404(Zap, id=id).delete()
    else: messages.error(request, "Interdit.")
    return redirect('manage_zap')

@login_required
def manage_fokontany(request, id=None):
    instance = get_object_or_404(Fokontany, id=id) if id else None
    if request.method == 'POST':
        if not has_perm(request.user, 'edit' if instance else 'add'): messages.error(request, "Accès refusé."); return redirect('manage_fokontany')
        nom, zap_id = clean_text(request.POST.get('nom_fokontany')), request.POST.get('zap_id')
        if nom and zap_id:
            if not filter_queryset_by_user(Zap.objects.all(), request.user, 'zap').filter(id=zap_id).exists() or (instance and not filter_queryset_by_user(Fokontany.objects.all(), request.user, 'fokontany').filter(id=instance.id).exists()):
                messages.error(request, "Alerte : Juridiction dépassée."); return redirect('manage_fokontany')
            if Fokontany.objects.filter(nom__iexact=nom, zap_id=zap_id).exclude(id=instance.id if instance else None).exists(): messages.error(request, "Fokontany existant.")
            else:
                if instance: instance.nom, instance.zap_id = nom, zap_id; instance.save()
                else: Fokontany.objects.create(nom=nom, zap_id=zap_id)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_fokontany')
                
    fokontanys = filter_queryset_by_user(Fokontany.objects.select_related('zap__cisco__dren'), request.user, 'fokontany').order_by('nom')
    return render(request, 'manage_fokontany.html', {'fokontanys': fokontanys, 'edit_obj': instance})

@login_required
def delete_fokontany(request, id):
    if not has_perm(request.user, 'delete'): return redirect('manage_fokontany')
    if filter_queryset_by_user(Fokontany.objects.all(), request.user, 'fokontany').filter(id=id).exists() and request.method == 'POST': get_object_or_404(Fokontany, id=id).delete()
    else: messages.error(request, "Interdit.")
    return redirect('manage_fokontany')

@login_required
def manage_etablissement(request, id=None):
    instance = get_object_or_404(Etablissement, id=id) if id else None
    if request.method == 'POST':
        if not has_perm(request.user, 'edit' if instance else 'add'): messages.error(request, "Accès refusé."); return redirect('manage_etablissement')
        nom, fokontany_id = clean_text(request.POST.get('nom_etablissement')), request.POST.get('fokontany_id')
        if nom and fokontany_id:
            if not filter_queryset_by_user(Fokontany.objects.all(), request.user, 'fokontany').filter(id=fokontany_id).exists() or (instance and not filter_queryset_by_user(Etablissement.objects.all(), request.user, 'etablissement').filter(id=instance.id).exists()):
                messages.error(request, "Alerte : Vous n'avez pas accès à cet emplacement."); return redirect('manage_etablissement')
            if Etablissement.objects.filter(nom__iexact=nom, fokontany_id=fokontany_id).exclude(id=instance.id if instance else None).exists(): messages.error(request, "Établissement existant.")
            else:
                if instance: instance.nom, instance.fokontany_id = nom, fokontany_id; instance.save()
                else: Etablissement.objects.create(nom=nom, fokontany_id=fokontany_id)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_etablissement')
                
    etablissements = filter_queryset_by_user(Etablissement.objects.select_related('fokontany__zap__cisco__dren'), request.user, 'etablissement').order_by('nom')
    return render(request, 'manage_etablissement.html', {'etablissements': etablissements, 'edit_obj': instance})

@login_required
def delete_etablissement(request, id):
    if not has_perm(request.user, 'delete'): return redirect('manage_etablissement')
    if filter_queryset_by_user(Etablissement.objects.all(), request.user, 'etablissement').filter(id=id).exists() and request.method == 'POST': get_object_or_404(Etablissement, id=id).delete()
    else: messages.error(request, "Interdit.")
    return redirect('manage_etablissement')

@login_required
def manage_portfolio(request, id=None):
    instance = get_object_or_404(LienPortfolio, id=id) if id else None
    if request.method == 'POST':
        if not has_perm(request.user, 'edit' if instance else 'add'): messages.error(request, "Accès refusé."); return redirect('manage_portfolio')
        cin, nom_prenom, lien = clean_text(request.POST.get('cin')), clean_text(request.POST.get('nom_prenom')), clean_text(request.POST.get('lien'))
        if cin and nom_prenom and lien:
            if LienPortfolio.objects.filter(cin__iexact=cin).exclude(id=instance.id if instance else None).exists(): messages.error(request, "CIN existant.")
            else:
                if instance: instance.cin, instance.nom_prenom, instance.lien = cin, nom_prenom, lien; instance.save()
                else: LienPortfolio.objects.create(cin=cin, nom_prenom=nom_prenom, lien=lien)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_portfolio')
    return render(request, 'manage_portfolio.html', {'portfolios': LienPortfolio.objects.order_by('-id'), 'edit_obj': instance})

@login_required
def delete_portfolio(request, id):
    if not has_perm(request.user, 'delete'): return redirect('manage_portfolio')
    if request.method == 'POST': get_object_or_404(LienPortfolio, id=id).delete()
    return redirect('manage_portfolio')

@login_required
def manage_presence(request, id=None):
    instance = get_object_or_404(Presence, id=id) if id else None
    personnes = LienPortfolio.objects.all().order_by('nom_prenom')
    if request.method == 'POST':
        if not has_perm(request.user, 'edit' if instance else 'add'): messages.error(request, "Accès refusé."); return redirect('manage_presence')
        p_id, e_id, d_deb, d_fin = request.POST.get('personne_id'), request.POST.get('etablissement_id'), request.POST.get('date_debut'), request.POST.get('date_fin') or None
        if p_id and e_id and d_deb:
            if not filter_queryset_by_user(Etablissement.objects.all(), request.user, 'etablissement').filter(id=e_id).exists() or (instance and not filter_queryset_by_user(Presence.objects.all(), request.user, 'presence').filter(id=instance.id).exists()):
                messages.error(request, "Alerte : Établissement hors de votre juridiction."); return redirect('manage_presence')
            if Presence.objects.filter(personne_id=p_id, etablissement_id=e_id, date_debut=d_deb).exclude(id=instance.id if instance else None).exists(): messages.error(request, "Doublon.")
            else:
                if instance: instance.personne_id, instance.etablissement_id, instance.date_debut, instance.date_fin = p_id, e_id, d_deb, d_fin; instance.save()
                else: Presence.objects.create(personne_id=p_id, etablissement_id=e_id, date_debut=d_deb, date_fin=d_fin)
                messages.success(request, "Affectation réussie."); return redirect('manage_presence')
    presences = filter_queryset_by_user(Presence.objects.select_related('personne', 'etablissement__fokontany__zap__cisco__dren'), request.user, 'presence').order_by('-date_debut')
    return render(request, 'manage_presence.html', {'presences': presences, 'personnes': personnes, 'edit_obj': instance})

@login_required
def delete_presence(request, id):
    if not has_perm(request.user, 'delete'): return redirect('manage_presence')
    if filter_queryset_by_user(Presence.objects.all(), request.user, 'presence').filter(id=id).exists() and request.method == 'POST': get_object_or_404(Presence, id=id).delete()
    else: messages.error(request, "Interdit.")
    return redirect('manage_presence')

@login_required
def export_data(request):
    if not request.user.is_superuser: messages.error(request, "Réservé à l'Admin National."); return redirect('index')
    all_objects = list(chain(Dren.objects.all(), Cisco.objects.all(), Zap.objects.all(), Fokontany.objects.all(), Etablissement.objects.all(), LienPortfolio.objects.all(), Presence.objects.all()))
    final_data = {"date_exportation": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "donnees_sqlite": json.loads(serializers.serialize('json', all_objects))}
    response = HttpResponse(json.dumps(final_data, indent=4), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="Sauvegarde_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
    return response

@login_required
def import_data(request):
    if not request.user.is_superuser: messages.error(request, "Réservé à l'Admin."); return redirect('index')
    if request.method == 'POST':
        json_file, hard_reset = request.FILES.get('json_file'), request.POST.get('hard_reset') == 'on'
        if not json_file: messages.error(request, "Fichier manquant."); return redirect('index')
        try:
            data = json.load(json_file)
            if isinstance(data, dict) and 'donnees_sqlite' in data:
                if hard_reset:
                    Presence.objects.all().delete(); LienPortfolio.objects.all().delete(); Etablissement.objects.all().delete(); Fokontany.objects.all().delete(); Zap.objects.all().delete(); Cisco.objects.all().delete(); Dren.objects.all().delete()
                compteur = 0
                for obj in serializers.deserialize("json", json.dumps(data['donnees_sqlite'])): obj.save(); compteur += 1
                msg = f"Importation réussie. {compteur} éléments intégrés."
                if hard_reset: msg += " (Hard Reset appliqué)."
                messages.success(request, msg)
            else: messages.error(request, "Format invalide.")
        except Exception as e: messages.error(request, f"Erreur : {str(e)}")
    return redirect('index')