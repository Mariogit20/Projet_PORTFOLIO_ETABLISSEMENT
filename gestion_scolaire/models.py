from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Dren(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nom

class Cisco(models.Model):
    nom = models.CharField(max_length=100)
    dren = models.ForeignKey(Dren, on_delete=models.CASCADE, related_name='ciscos')
    class Meta: unique_together = ('nom', 'dren')
    def __str__(self): return self.nom

class Zap(models.Model):
    nom = models.CharField(max_length=100)
    cisco = models.ForeignKey(Cisco, on_delete=models.CASCADE, related_name='zaps')
    class Meta: unique_together = ('nom', 'cisco')
    def __str__(self): return self.nom

class Fokontany(models.Model):
    nom = models.CharField(max_length=100)
    zap = models.ForeignKey(Zap, on_delete=models.CASCADE, related_name='fokontanys')
    class Meta: unique_together = ('nom', 'zap')
    def __str__(self): return self.nom

class Etablissement(models.Model):
    nom = models.CharField(max_length=150)
    fokontany = models.ForeignKey(Fokontany, on_delete=models.CASCADE, related_name='etablissements')
    class Meta: unique_together = ('nom', 'fokontany')
    def __str__(self): return self.nom

class LienPortfolio(models.Model):
    cin = models.CharField(max_length=20, unique=True, verbose_name="Numéro de CIN")
    nom_prenom = models.CharField(max_length=150, verbose_name="Nom et Prénom")
    lien = models.URLField(max_length=255, verbose_name="Lien du portfolio")
    etablissements = models.ManyToManyField(Etablissement, through='Presence', related_name='liens_portfolio')
    def __str__(self): return f"{self.nom_prenom} (CIN: {self.cin})"

class Presence(models.Model):
    personne = models.ForeignKey(LienPortfolio, on_delete=models.CASCADE, related_name='presences')
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, related_name='presences')
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    class Meta:
        unique_together = ('personne', 'etablissement', 'date_debut')
        verbose_name = "Présence"
        verbose_name_plural = "Présences"
    def __str__(self): return f"{self.personne.nom_prenom} - {self.etablissement.nom}"

# ==========================================
# SÉCURITÉ & RESTRICTION GÉOGRAPHIQUE GLOBALE
# ==========================================
class UserProfile(models.Model):
    ROLES = (
        ('ADMIN', 'Administrateur National'),
        ('DREN', 'Responsable DREN'),
        ('CISCO', 'Responsable CISCO'),
        ('ZAP', 'Responsable ZAP'),
        ('FOKONTANY', 'Responsable Fokontany'),
        ('ETAB', 'Directeur Établissement'),
        ('INVITE', 'Invité (Lecture seule)'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLES, default='INVITE')
    can_add = models.BooleanField(default=False, verbose_name="Peut Ajouter")
    can_edit = models.BooleanField(default=False, verbose_name="Peut Modifier")
    can_delete = models.BooleanField(default=False, verbose_name="Peut Supprimer")
    
    # LIMITATIONS STRICTES MULTI-NIVEAUX
    dren_assignee = models.ForeignKey(Dren, on_delete=models.SET_NULL, null=True, blank=True)
    cisco_assignee = models.ForeignKey(Cisco, on_delete=models.SET_NULL, null=True, blank=True)
    zap_assignee = models.ForeignKey(Zap, on_delete=models.SET_NULL, null=True, blank=True)
    fokontany_assignee = models.ForeignKey(Fokontany, on_delete=models.SET_NULL, null=True, blank=True)
    etablissement_assignee = models.ForeignKey(Etablissement, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self): return f"{self.user.username} - {self.get_role_display()}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created: UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()