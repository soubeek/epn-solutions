#!/usr/bin/env python
"""
Script pour créer des données de test
Usage: python create_test_data.py
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.utilisateurs.models import Utilisateur
from apps.postes.models import Poste
from apps.sessions.models import Session
from apps.logs.models import Log


def create_test_data():
    print("🚀 Création des données de test...")

    # 1. Créer des utilisateurs
    print("\n📋 Création des utilisateurs...")
    users_data = [
        {
            'nom': 'Dupont',
            'prenom': 'Jean',
            'email': 'jean.dupont@example.re',
            'telephone': '0692123456',
            'carte_identite': 'CNI123456',
            'adresse': '12 Rue de la République, Saint-Denis',
            'date_naissance': '1985-05-15',
            'created_by': 'admin'
        },
        {
            'nom': 'Martin',
            'prenom': 'Marie',
            'email': 'marie.martin@example.re',
            'telephone': '0692234567',
            'carte_identite': 'CNI234567',
            'adresse': '45 Avenue du Général de Gaulle, Saint-Paul',
            'date_naissance': '1990-08-22',
            'created_by': 'admin'
        },
        {
            'nom': 'Bernard',
            'prenom': 'Pierre',
            'email': 'pierre.bernard@example.re',
            'telephone': '0692345678',
            'carte_identite': 'CNI345678',
            'adresse': '78 Rue du Marché, Saint-Pierre',
            'date_naissance': '1978-12-03',
            'created_by': 'admin'
        },
        {
            'nom': 'Leroy',
            'prenom': 'Sophie',
            'email': 'sophie.leroy@example.re',
            'telephone': '0692456789',
            'carte_identite': 'CNI456789',
            'adresse': '23 Chemin des Jardins, Le Tampon',
            'date_naissance': '1995-03-10',
            'created_by': 'admin'
        },
        {
            'nom': 'Moreau',
            'prenom': 'Luc',
            'email': 'luc.moreau@example.re',
            'telephone': '0692567890',
            'carte_identite': 'CNI567890',
            'adresse': '56 Boulevard de la Mer, Saint-Leu',
            'date_naissance': '1982-07-28',
            'created_by': 'admin'
        }
    ]

    created_users = []
    for user_data in users_data:
        user, created = Utilisateur.objects.get_or_create(
            carte_identite=user_data['carte_identite'],
            defaults=user_data
        )
        if created:
            print(f"  ✅ Créé: {user.get_full_name()}")
        else:
            print(f"  ℹ️  Existe déjà: {user.get_full_name()}")
        created_users.append(user)

    # 2. Créer des postes
    print("\n💻 Création des postes...")
    postes_data = [
        {
            'nom': 'Poste-01',
            'ip_address': '192.168.1.101',
            'mac_address': 'AA:BB:CC:DD:EE:01',
            'statut': 'disponible',
            'emplacement': 'Salle principale - Rangée A',
            'version_client': '1.0.0'
        },
        {
            'nom': 'Poste-02',
            'ip_address': '192.168.1.102',
            'mac_address': 'AA:BB:CC:DD:EE:02',
            'statut': 'disponible',
            'emplacement': 'Salle principale - Rangée A',
            'version_client': '1.0.0'
        },
        {
            'nom': 'Poste-03',
            'ip_address': '192.168.1.103',
            'mac_address': 'AA:BB:CC:DD:EE:03',
            'statut': 'occupe',
            'emplacement': 'Salle principale - Rangée B',
            'version_client': '1.0.0',
            'derniere_connexion': timezone.now()
        },
        {
            'nom': 'Poste-04',
            'ip_address': '192.168.1.104',
            'mac_address': 'AA:BB:CC:DD:EE:04',
            'statut': 'disponible',
            'emplacement': 'Salle principale - Rangée B',
            'version_client': '1.0.0'
        },
        {
            'nom': 'Poste-05',
            'ip_address': '192.168.1.105',
            'mac_address': 'AA:BB:CC:DD:EE:05',
            'statut': 'maintenance',
            'emplacement': 'Salle annexe',
            'version_client': '0.9.5',
            'notes': 'Clavier à remplacer'
        },
        {
            'nom': 'Poste-06',
            'ip_address': '192.168.1.106',
            'mac_address': 'AA:BB:CC:DD:EE:06',
            'statut': 'hors_ligne',
            'emplacement': 'Salle annexe',
            'version_client': '1.0.0'
        }
    ]

    created_postes = []
    for poste_data in postes_data:
        poste, created = Poste.objects.get_or_create(
            nom=poste_data['nom'],
            defaults=poste_data
        )
        if created:
            print(f"  ✅ Créé: {poste.nom} ({poste.statut})")
        else:
            print(f"  ℹ️  Existe déjà: {poste.nom}")
        created_postes.append(poste)

    # 3. Créer des sessions
    print("\n🎮 Création des sessions...")

    # Session active
    if len(created_users) > 0 and len(created_postes) > 2:
        session1, created = Session.objects.get_or_create(
            code_acces='ABC123',
            defaults={
                'utilisateur': created_users[0],
                'poste': created_postes[2],  # Poste-03 (occupé)
                'duree_initiale': 7200,  # 2 heures
                'temps_restant': 5400,   # 1h30 restant
                'debut_session': timezone.now() - timedelta(minutes=30),
                'statut': 'active',
                'operateur': 'admin'
            }
        )
        if created:
            print(f"  ✅ Session active créée: {session1.code_acces}")

        # Session terminée
        session2, created = Session.objects.get_or_create(
            code_acces='XYZ789',
            defaults={
                'utilisateur': created_users[1],
                'poste': created_postes[0],
                'duree_initiale': 3600,  # 1 heure
                'temps_restant': 0,
                'debut_session': timezone.now() - timedelta(hours=3),
                'fin_session': timezone.now() - timedelta(hours=2),
                'statut': 'terminee',
                'operateur': 'admin'
            }
        )
        if created:
            print(f"  ✅ Session terminée créée: {session2.code_acces}")

        # Session en attente
        session3, created = Session.objects.get_or_create(
            code_acces='DEF456',
            defaults={
                'utilisateur': created_users[2],
                'poste': created_postes[1],
                'duree_initiale': 5400,  # 1h30
                'temps_restant': 5400,
                'statut': 'en_attente',
                'operateur': 'admin'
            }
        )
        if created:
            print(f"  ✅ Session en attente créée: {session3.code_acces}")

    # 4. Créer des logs
    print("\n📝 Création des logs...")

    logs_data = [
        {
            'action': 'connexion_operateur',
            'operateur': 'admin',
            'details': 'Connexion réussie',
            'ip_address': '127.0.0.1'
        },
        {
            'action': 'creation_utilisateur',
            'operateur': 'admin',
            'details': f'Création de l\'utilisateur {created_users[0].get_full_name()}',
            'ip_address': '127.0.0.1'
        },
        {
            'action': 'generation_code',
            'operateur': 'admin',
            'details': 'Code ABC123 généré pour session',
            'ip_address': '127.0.0.1'
        },
        {
            'action': 'demarrage_session',
            'operateur': 'system',
            'details': f'Session ABC123 démarrée sur {created_postes[2].nom}',
            'ip_address': '192.168.1.103'
        },
        {
            'action': 'info',
            'operateur': 'system',
            'details': 'Système de gestion des postes démarré',
            'ip_address': '127.0.0.1'
        }
    ]

    for log_data in logs_data:
        log = Log.objects.create(**log_data)
        print(f"  ✅ Log créé: {log.action}")

    print("\n" + "="*60)
    print("✅ Données de test créées avec succès !")
    print("="*60)
    print(f"\n📊 Résumé:")
    print(f"  - Utilisateurs: {Utilisateur.objects.count()}")
    print(f"  - Postes: {Poste.objects.count()}")
    print(f"  - Sessions: {Session.objects.count()}")
    print(f"  - Logs: {Log.objects.count()}")
    print("\n🌐 Testez maintenant l'application sur http://localhost:3000/")
    print("   Credentials: admin / admin123")


if __name__ == '__main__':
    try:
        create_test_data()
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
