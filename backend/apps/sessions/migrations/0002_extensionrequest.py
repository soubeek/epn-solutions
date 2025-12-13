# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('poste_sessions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExtensionRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('minutes_requested', models.IntegerField(default=15, help_text='Nombre de minutes de prolongation demandées', verbose_name='Minutes demandées')),
                ('statut', models.CharField(choices=[('pending', 'En attente'), ('approved', 'Approuvée'), ('denied', 'Refusée'), ('expired', 'Expirée')], default='pending', max_length=20, verbose_name='Statut')),
                ('responded_by', models.CharField(blank=True, max_length=100, null=True, verbose_name='Répondu par')),
                ('responded_at', models.DateTimeField(blank=True, null=True, verbose_name='Date de réponse')),
                ('response_message', models.CharField(blank=True, max_length=255, null=True, verbose_name='Message de réponse')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extension_requests', to='poste_sessions.session', verbose_name='Session')),
            ],
            options={
                'verbose_name': 'Demande de prolongation',
                'verbose_name_plural': 'Demandes de prolongation',
                'db_table': 'extension_requests',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='extensionrequest',
            index=models.Index(fields=['statut'], name='extension_r_statut_6a8e5c_idx'),
        ),
        migrations.AddIndex(
            model_name='extensionrequest',
            index=models.Index(fields=['session', 'statut'], name='extension_r_session_3c2f4a_idx'),
        ),
        migrations.AddIndex(
            model_name='extensionrequest',
            index=models.Index(fields=['-created_at'], name='extension_r_created_8b7d9e_idx'),
        ),
    ]
