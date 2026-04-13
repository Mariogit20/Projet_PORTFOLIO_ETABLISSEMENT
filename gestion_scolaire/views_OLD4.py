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

def clean_text(text):
    return " ".join(text.split()) if text else None

def has_perm(user, action):
    if user.is_superuser: return True
    try: profile = user.profile
    except: return False
    if action == 'add': return profile.can_add
    if action == 'edit': return profile.can_edit
    if action == 'delete': return profile.can_delete
    return False

def get_dren_limit(user):
    if not user.is_superuser and hasattr(user, 'profile') and user.profile.dren_assignee:
        return user.profile.dren_assignee
    return None

@login_required
def manage_users(request, id=None):
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé. Réservé à l'Administrateur National.")
        return redirect('index')
    
    instance = get_object_or_404(User, id=id) if id else None
    if request.method == 'POST':
        username = clean_text(request.POST.get('username'))
        password = request.POST.get('password')
        is_superuser = request.POST.get('is_superuser') == 'on'
        role = request.POST.get('role', 'INVITE')
        can_add = request.POST.get('can_add') == 'on'
        can_edit = request.POST.get('can_edit') == 'on'
        can_delete = request.POST.get('can_delete') == 'on'
        dren_id = request.POST.get('dren_assignee')
        
        if username:
            if User.objects.filter(username__iexact=username).exclude(id=instance.id if instance else None).exists():
                messages.error(request, f"Le login '{username}' est déjà pris.")
            else:
                if instance:
                    instance.username, instance.is_superuser, instance.is_staff = username, is_superuser, is_superuser
                    if password: instance.set_password(password)
                    instance.save(); user_to_update = instance
                else:
                    if not password:
                        messages.error(request, "Mot de passe obligatoire."); return redirect('manage_users')
                    user_to_update = User.objects.create_user(username=username, password=password)
                    user_to_update.is_superuser, user_to_update.is_staff = is_superuser, is_superuser
                    user_to_update.save()
                
                profile = user_to_update.profile
                profile.role = role
                profile.can_add = can_add if not is_superuser else True
                profile.can_edit = can_edit if not is_superuser else True
                profile.can_delete = can_delete if not is_superuser else True
                profile.dren_assignee_id = dren_id if dren_id else None
                profile.save()
                
                messages.success(request, "Utilisateur enregistré avec ses droits et restrictions.")
                return redirect('manage_users')
                
    context = {
        'utilisateurs': User.objects.all().select_related('profile').order_by('-id'),
        'edit_obj': instance,
        'drens': Dren.objects.all().order_by('nom')
    }
    return render(request, 'manage_users.html', context)

@login_required
def delete_user(request, id):
    if not request.user.is_superuser: return redirect('index')
    if request.method == 'POST':
        user = get_object_or_404(User, id=id)
        if user == request.user: messages.error(request, "Impossible de supprimer votre propre compte.")
        else: user.delete(); messages.success(request, "Utilisateur supprimé.")
    return redirect('manage_users')

@login_required
def index_crud(request):
    return render(request, 'index.html')

@login_required
def search_autocomplete(request):
    term, entity_type, parent_id = request.GET.get('term', ''), request.GET.get('type', ''), request.GET.get('parent_id', '')
    dren_limit = get_dren_limit(request.user)
    
    if entity_type == 'dren': queryset = Dren.objects.all()
    elif entity_type == 'cisco' and parent_id: queryset = Cisco.objects.filter(dren_id=parent_id)
    elif entity_type == 'zap' and parent_id: queryset = Zap.objects.filter(cisco_id=parent_id)
    elif entity_type == 'fokontany' and parent_id: queryset = Fokontany.objects.filter(zap_id=parent_id)
    elif entity_type == 'etablissement' and parent_id: queryset = Etablissement.objects.filter(fokontany_id=parent_id)
    elif entity_type == 'etablissement_global': queryset = Etablissement.objects.select_related('fokontany__zap__cisco__dren').all()
    else: return JsonResponse([], safe=False)

    if dren_limit:
        if entity_type == 'dren': queryset = queryset.filter(id=dren_limit.id)
        elif entity_type == 'cisco': queryset = queryset.filter(dren=dren_limit)
        elif entity_type == 'zap': queryset = queryset.filter(cisco__dren=dren_limit)
        elif entity_type == 'fokontany': queryset = queryset.filter(zap__cisco__dren=dren_limit)
        elif 'etablissement' in entity_type: queryset = queryset.filter(fokontany__zap__cisco__dren=dren_limit)

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
    dren_limit = get_dren_limit(request.user)
    
    if request.method == 'POST':
        action = 'edit' if instance else 'add'
        if not has_perm(request.user, action):
            messages.error(request, "Accès refusé."); return redirect('manage_dren')
            
        if dren_limit and (not instance or instance.id != dren_limit.id):
            messages.error(request, "Alerte : Vous ne pouvez modifier que votre propre DREN."); return redirect('manage_dren')

        nom = clean_text(request.POST.get('nom_dren'))
        if nom:
            if Dren.objects.filter(nom__iexact=nom).exclude(id=instance.id if instance else None).exists():
                messages.error(request, f"La DREN '{nom}' existe déjà.")
            else:
                if instance: instance.nom = nom; instance.save()
                else: Dren.objects.create(nom=nom)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_dren')
                
    drens = Dren.objects.order_by('nom')
    if dren_limit: drens = drens.filter(id=dren_limit.id)
    return render(request, 'manage_dren.html', {'drens': drens, 'edit_obj': instance})

@login_required
def delete_dren(request, id):
    if not has_perm(request.user, 'delete'): messages.error(request, "Accès refusé."); return redirect('manage_dren')
    dren_cible = get_object_or_404(Dren, id=id)
    dren_limit = get_dren_limit(request.user)
    if dren_limit and dren_cible.id != dren_limit.id:
        messages.error(request, "Interdit : Hors de votre juridiction."); return redirect('manage_dren')
        
    if request.method == 'POST': dren_cible.delete()
    return redirect('manage_dren')

@login_required
def manage_cisco(request, id=None):
    instance = get_object_or_404(Cisco, id=id) if id else None
    dren_limit = get_dren_limit(request.user)
    
    if request.method == 'POST':
        action = 'edit' if instance else 'add'
        if not has_perm(request.user, action):
            messages.error(request, "Accès refusé."); return redirect('manage_cisco')
            
        nom, dren_id = clean_text(request.POST.get('nom_cisco')), request.POST.get('dren_id')
        if nom and dren_id:
            if dren_limit and int(dren_id) != dren_limit.id:
                messages.error(request, "Alerte de Sécurité : Vous n'avez pas le droit d'ajouter une CISCO dans une autre DREN."); return redirect('manage_cisco')
                
            if Cisco.objects.filter(nom__iexact=nom, dren_id=dren_id).exclude(id=instance.id if instance else None).exists():
                messages.error(request, f"La CISCO '{nom}' existe déjà dans cette DREN.")
            else:
                if instance: instance.nom, instance.dren_id = nom, dren_id; instance.save()
                else: Cisco.objects.create(nom=nom, dren_id=dren_id)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_cisco')
                
    ciscos = Cisco.objects.select_related('dren').order_by('nom')
    if dren_limit: ciscos = ciscos.filter(dren=dren_limit)
    return render(request, 'manage_cisco.html', {'ciscos': ciscos, 'edit_obj': instance})

@login_required
def delete_cisco(request, id):
    if not has_perm(request.user, 'delete'): messages.error(request, "Accès refusé."); return redirect('manage_cisco')
    cisco_cible = get_object_or_404(Cisco, id=id)
    dren_limit = get_dren_limit(request.user)
    if dren_limit and cisco_cible.dren != dren_limit:
        messages.error(request, "Interdit : Hors de votre juridiction."); return redirect('manage_cisco')
        
    if request.method == 'POST': cisco_cible.delete()
    return redirect('manage_cisco')

@login_required
def manage_zap(request, id=None):
    instance = get_object_or_404(Zap, id=id) if id else None
    dren_limit = get_dren_limit(request.user)
    
    if request.method == 'POST':
        action = 'edit' if instance else 'add'
        if not has_perm(request.user, action):
            messages.error(request, "Accès refusé."); return redirect('manage_zap')
            
        nom, cisco_id = clean_text(request.POST.get('nom_zap')), request.POST.get('cisco_id')
        if nom and cisco_id:
            cisco_parente = get_object_or_404(Cisco, id=cisco_id)
            if dren_limit and cisco_parente.dren != dren_limit:
                messages.error(request, "Alerte de Sécurité : Vous n'avez pas le droit d'ajouter une ZAP dans une autre DREN."); return redirect('manage_zap')

            if Zap.objects.filter(nom__iexact=nom, cisco_id=cisco_id).exclude(id=instance.id if instance else None).exists():
                messages.error(request, f"La ZAP '{nom}' existe déjà dans cette CISCO.")
            else:
                if instance: instance.nom, instance.cisco_id = nom, cisco_id; instance.save()
                else: Zap.objects.create(nom=nom, cisco_id=cisco_id)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_zap')
                
    zaps = Zap.objects.select_related('cisco__dren').order_by('nom')
    if dren_limit: zaps = zaps.filter(cisco__dren=dren_limit)
    return render(request, 'manage_zap.html', {'zaps': zaps, 'edit_obj': instance})

@login_required
def delete_zap(request, id):
    if not has_perm(request.user, 'delete'): messages.error(request, "Accès refusé."); return redirect('manage_zap')
    zap_cible = get_object_or_404(Zap, id=id)
    dren_limit = get_dren_limit(request.user)
    if dren_limit and zap_cible.cisco.dren != dren_limit:
        messages.error(request, "Interdit : Hors de votre juridiction."); return redirect('manage_zap')
        
    if request.method == 'POST': zap_cible.delete()
    return redirect('manage_zap')

@login_required
def manage_fokontany(request, id=None):
    instance = get_object_or_404(Fokontany, id=id) if id else None
    dren_limit = get_dren_limit(request.user)
    
    if request.method == 'POST':
        action = 'edit' if instance else 'add'
        if not has_perm(request.user, action):
            messages.error(request, "Accès refusé."); return redirect('manage_fokontany')
            
        nom, zap_id = clean_text(request.POST.get('nom_fokontany')), request.POST.get('zap_id')
        if nom and zap_id:
            zap_parente = get_object_or_404(Zap, id=zap_id)
            if dren_limit and zap_parente.cisco.dren != dren_limit:
                messages.error(request, "Alerte : Impossible de créer un Fokontany dans une autre DREN."); return redirect('manage_fokontany')

            if Fokontany.objects.filter(nom__iexact=nom, zap_id=zap_id).exclude(id=instance.id if instance else None).exists():
                messages.error(request, f"Le Fokontany '{nom}' existe déjà dans cette ZAP.")
            else:
                if instance: instance.nom, instance.zap_id = nom, zap_id; instance.save()
                else: Fokontany.objects.create(nom=nom, zap_id=zap_id)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_fokontany')
                
    fokontanys = Fokontany.objects.select_related('zap__cisco__dren').order_by('nom')
    if dren_limit: fokontanys = fokontanys.filter(zap__cisco__dren=dren_limit)
    return render(request, 'manage_fokontany.html', {'fokontanys': fokontanys, 'edit_obj': instance})

@login_required
def delete_fokontany(request, id):
    if not has_perm(request.user, 'delete'): messages.error(request, "Accès refusé."); return redirect('manage_fokontany')
    fk_cible = get_object_or_404(Fokontany, id=id)
    dren_limit = get_dren_limit(request.user)
    if dren_limit and fk_cible.zap.cisco.dren != dren_limit:
        messages.error(request, "Interdit : Hors de votre juridiction."); return redirect('manage_fokontany')
        
    if request.method == 'POST': fk_cible.delete()
    return redirect('manage_fokontany')

@login_required
def manage_etablissement(request, id=None):
    instance = get_object_or_404(Etablissement, id=id) if id else None
    dren_limit = get_dren_limit(request.user)
    
    if request.method == 'POST':
        action = 'edit' if instance else 'add'
        if not has_perm(request.user, action):
            messages.error(request, "Accès refusé."); return redirect('manage_etablissement')
            
        nom, fokontany_id = clean_text(request.POST.get('nom_etablissement')), request.POST.get('fokontany_id')
        if nom and fokontany_id:
            fk_parent = get_object_or_404(Fokontany, id=fokontany_id)
            if dren_limit and fk_parent.zap.cisco.dren != dren_limit:
                messages.error(request, "Alerte : Impossible d'ajouter un établissement hors de votre DREN."); return redirect('manage_etablissement')

            if Etablissement.objects.filter(nom__iexact=nom, fokontany_id=fokontany_id).exclude(id=instance.id if instance else None).exists():
                messages.error(request, f"L'établissement '{nom}' existe déjà dans ce Fokontany.")
            else:
                if instance: instance.nom, instance.fokontany_id = nom, fokontany_id; instance.save()
                else: Etablissement.objects.create(nom=nom, fokontany_id=fokontany_id)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_etablissement')
                
    etablissements = Etablissement.objects.select_related('fokontany__zap__cisco__dren').order_by('nom')
    if dren_limit: etablissements = etablissements.filter(fokontany__zap__cisco__dren=dren_limit)
    return render(request, 'manage_etablissement.html', {'etablissements': etablissements, 'edit_obj': instance})

@login_required
def delete_etablissement(request, id):
    if not has_perm(request.user, 'delete'): messages.error(request, "Accès refusé."); return redirect('manage_etablissement')
    etab_cible = get_object_or_404(Etablissement, id=id)
    dren_limit = get_dren_limit(request.user)
    if dren_limit and etab_cible.fokontany.zap.cisco.dren != dren_limit:
        messages.error(request, "Interdit : Hors de votre juridiction."); return redirect('manage_etablissement')
        
    if request.method == 'POST': etab_cible.delete()
    return redirect('manage_etablissement')

@login_required
def manage_portfolio(request, id=None):
    instance = get_object_or_404(LienPortfolio, id=id) if id else None
    if request.method == 'POST':
        action = 'edit' if instance else 'add'
        if not has_perm(request.user, action):
            messages.error(request, "Accès refusé."); return redirect('manage_portfolio')
            
        cin, nom_prenom, lien = clean_text(request.POST.get('cin')), clean_text(request.POST.get('nom_prenom')), clean_text(request.POST.get('lien'))
        if cin and nom_prenom and lien:
            if LienPortfolio.objects.filter(cin__iexact=cin).exclude(id=instance.id if instance else None).exists():
                messages.error(request, f"Le CIN '{cin}' est déjà enregistré.")
            else:
                if instance: instance.cin, instance.nom_prenom, instance.lien = cin, nom_prenom, lien; instance.save()
                else: LienPortfolio.objects.create(cin=cin, nom_prenom=nom_prenom, lien=lien)
                messages.success(request, "Enregistrement réussi."); return redirect('manage_portfolio')
                
    return render(request, 'manage_portfolio.html', {'portfolios': LienPortfolio.objects.order_by('-id'), 'edit_obj': instance})

@login_required
def delete_portfolio(request, id):
    if not has_perm(request.user, 'delete'): messages.error(request, "Accès refusé."); return redirect('manage_portfolio')
    if request.method == 'POST': get_object_or_404(LienPortfolio, id=id).delete()
    return redirect('manage_portfolio')

@login_required
def manage_presence(request, id=None):
    instance = get_object_or_404(Presence, id=id) if id else None
    dren_limit = get_dren_limit(request.user)
    personnes = LienPortfolio.objects.all().order_by('nom_prenom')
    
    if request.method == 'POST':
        action = 'edit' if instance else 'add'
        if not has_perm(request.user, action):
            messages.error(request, "Accès refusé."); return redirect('manage_presence')
            
        p_id, e_id, d_deb, d_fin = request.POST.get('personne_id'), request.POST.get('etablissement_id'), request.POST.get('date_debut'), request.POST.get('date_fin') or None
        if p_id and e_id and d_deb:
            etab = get_object_or_404(Etablissement, id=e_id)
            if dren_limit and etab.fokontany.zap.cisco.dren != dren_limit:
                messages.error(request, "Alerte : Vous ne pouvez pas affecter une personne hors de votre DREN."); return redirect('manage_presence')

            if Presence.objects.filter(personne_id=p_id, etablissement_id=e_id, date_debut=d_deb).exclude(id=instance.id if instance else None).exists():
                messages.error(request, "Affectation en doublon pour cette date.")
            else:
                if instance: instance.personne_id, instance.etablissement_id, instance.date_debut, instance.date_fin = p_id, e_id, d_deb, d_fin; instance.save()
                else: Presence.objects.create(personne_id=p_id, etablissement_id=e_id, date_debut=d_deb, date_fin=d_fin)
                messages.success(request, "Affectation réussie."); return redirect('manage_presence')
                
    presences = Presence.objects.select_related('personne', 'etablissement__fokontany__zap__cisco__dren').order_by('-date_debut')
    if dren_limit: presences = presences.filter(etablissement__fokontany__zap__cisco__dren=dren_limit)
    return render(request, 'manage_presence.html', {'presences': presences, 'personnes': personnes, 'edit_obj': instance})

@login_required
def delete_presence(request, id):
    if not has_perm(request.user, 'delete'): messages.error(request, "Accès refusé."); return redirect('manage_presence')
    pres_cible = get_object_or_404(Presence, id=id)
    dren_limit = get_dren_limit(request.user)
    if dren_limit and pres_cible.etablissement.fokontany.zap.cisco.dren != dren_limit:
        messages.error(request, "Interdit : Hors de votre juridiction."); return redirect('manage_presence')
        
    if request.method == 'POST': pres_cible.delete()
    return redirect('manage_presence')

@login_required
def export_data(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé. Réservé à l'Admin National."); return redirect('index')
    all_objects = list(chain(Dren.objects.all(), Cisco.objects.all(), Zap.objects.all(), Fokontany.objects.all(), Etablissement.objects.all(), LienPortfolio.objects.all(), Presence.objects.all()))
    final_data = {"date_exportation": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "donnees_sqlite": json.loads(serializers.serialize('json', all_objects))}
    response = HttpResponse(json.dumps(final_data, indent=4), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="Sauvegarde_Scolaire_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
    return response

@login_required
def import_data(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé. Réservé à l'Admin National."); return redirect('index')
    
    if request.method == 'POST':
        json_file = request.FILES.get('json_file')
        hard_reset = request.POST.get('hard_reset') == 'on'
        
        if not json_file:
            messages.error(request, "Veuillez sélectionner un fichier JSON."); return redirect('index')
        
        try:
            data = json.load(json_file)
            if isinstance(data, dict) and 'donnees_sqlite' in data:
                if hard_reset:
                    Presence.objects.all().delete()
                    LienPortfolio.objects.all().delete()
                    Etablissement.objects.all().delete()
                    Fokontany.objects.all().delete()
                    Zap.objects.all().delete()
                    Cisco.objects.all().delete()
                    Dren.objects.all().delete()
                
                compteur = 0
                for obj in serializers.deserialize("json", json.dumps(data['donnees_sqlite'])):
                    obj.save()
                    compteur += 1
                
                msg_succes = f"Importation réussie de l'archive [{data.get('date_exportation', 'Inconnue')}]. {compteur} éléments intégrés."
                if hard_reset: msg_succes += " ⚠️ (Le Hard Reset a purgé les anciennes données avec succès)."
                messages.success(request, msg_succes)
            else: 
                messages.error(request, "Format de fichier invalide.")
        except Exception as e: 
            messages.error(request, f"Erreur lors de l'importation : {str(e)}")
            
    return redirect('index')