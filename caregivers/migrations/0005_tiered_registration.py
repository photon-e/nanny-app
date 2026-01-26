# Generated manually for tiered registration

import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('caregivers', '0004_caregiverprofile_profile_image'),
    ]

    operations = [
        # Update location field to allow blank
        migrations.AlterField(
            model_name='caregiverprofile',
            name='location',
            field=models.CharField(blank=True, max_length=255),
        ),
        # Add tiered registration fields
        migrations.AddField(
            model_name='caregiverprofile',
            name='registration_level',
            field=models.IntegerField(choices=[(1, 'Level 1 - Basic'), (2, 'Level 2 - Identity'), (3, 'Level 3 - Guarantors')], default=1),
        ),
        migrations.AddField(
            model_name='caregiverprofile',
            name='phone',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='caregiverprofile',
            name='age',
            field=models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(18)]),
        ),
        migrations.AddField(
            model_name='caregiverprofile',
            name='nin_document',
            field=models.FileField(blank=True, null=True, upload_to='nin_documents/'),
        ),
        migrations.AddField(
            model_name='caregiverprofile',
            name='selfie_photo',
            field=models.ImageField(blank=True, null=True, upload_to='selfie_photos/'),
        ),
        # Create Guarantor model
        migrations.CreateModel(
            name='Guarantor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=255)),
                ('nin', models.CharField(max_length=20)),
                ('phone', models.CharField(max_length=20)),
                ('phone_verified', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('caregiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='guarantors', to='caregivers.caregiverprofile')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
