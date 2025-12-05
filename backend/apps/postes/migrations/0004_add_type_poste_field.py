# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('postes', '0003_add_discovery_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='poste',
            name='type_poste',
            field=models.CharField(
                choices=[('bureautique', 'Bureautique'), ('gaming', 'Gaming')],
                default='bureautique',
                help_text='Bureautique (navigateur, office) ou Gaming (Steam, launchers)',
                max_length=20,
                verbose_name='Type de poste'
            ),
        ),
    ]
