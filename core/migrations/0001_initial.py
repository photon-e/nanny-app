# Generated manually - Admin features and invisible features

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('caregivers', '0007_new_features'),
        ('families', '0002_parent_features'),
    ]

    operations = [
        migrations.CreateModel(
            name='Blacklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nin', models.CharField(db_index=True, max_length=20, unique=True)),
                ('reason', models.CharField(help_text='Reason for blacklist (theft, abuse, etc.)', max_length=255)),
                ('banned_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True)),
                ('banned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-banned_at'],
            },
        ),
        migrations.CreateModel(
            name='Dispute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('open', 'Open'), ('investigating', 'Under Investigation'), ('resolved', 'Resolved'), ('dismissed', 'Dismissed')], default='open', max_length=20)),
                ('admin_notes', models.TextField(blank=True)),
                ('caregiver_payout_frozen', models.BooleanField(default=False)),
                ('family_account_banned', models.BooleanField(default=False)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('incident', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='dispute', to='families.incidentreport')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_disputes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GeofenceCheckin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expected_lat', models.DecimalField(decimal_places=6, max_digits=9)),
                ('expected_lng', models.DecimalField(decimal_places=6, max_digits=9)),
                ('actual_lat', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('actual_lng', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('verified', models.BooleanField(default=False, help_text='GPS confirmed at location')),
                ('checkin_time', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checkins', to='families.booking')),
                ('caregiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checkins', to='caregivers.caregiverprofile')),
            ],
            options={
                'ordering': ['-checkin_time'],
            },
        ),
        migrations.CreateModel(
            name='MonitoredMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('flagged', models.BooleanField(default=False, help_text='Flagged for review (harassment, private deal solicitation)')),
                ('flagged_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='families.booking')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='PanicAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alert_type', models.CharField(choices=[('sos', 'SOS/Emergency'), ('safety', 'Safety Concern'), ('medical', 'Medical Emergency')], default='sos', max_length=20)),
                ('location_lat', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('location_lng', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('message', models.TextField(blank=True)),
                ('acknowledged', models.BooleanField(default=False)),
                ('acknowledged_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('acknowledged_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='acknowledged_alerts', to=settings.AUTH_USER_MODEL)),
                ('triggered_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='panic_alerts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ServiceAgreement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdf_file', models.FileField(blank=True, null=True, upload_to='service_agreements/')),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('sent_to_family', models.BooleanField(default=False)),
                ('sent_to_caregiver', models.BooleanField(default=False)),
                ('booking', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='agreement', to='families.booking')),
            ],
        ),
    ]
