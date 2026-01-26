# Generated manually - Change age field to date_of_birth

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('caregivers', '0005_tiered_registration'),
    ]

    operations = [
        # Remove age field
        migrations.RemoveField(
            model_name='caregiverprofile',
            name='age',
        ),
        # Add date_of_birth field
        migrations.AddField(
            model_name='caregiverprofile',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True),
        ),
    ]
