# Generated manually - New features: Code of Conduct, Training, Availability, Earnings

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('caregivers', '0006_change_age_to_date_of_birth'),
    ]

    operations = [
        # Add new fields to CaregiverProfile
        migrations.AddField(
            model_name='caregiverprofile',
            name='is_available',
            field=models.BooleanField(default=False, help_text='Toggle to control visibility to parents'),
        ),
        migrations.AddField(
            model_name='caregiverprofile',
            name='code_of_conduct_signed',
            field=models.BooleanField(default=False),
        ),
        
        # Code of Conduct Signature
        migrations.CreateModel(
            name='CodeOfConductSignature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('signed_at', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('caregiver', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='code_of_conduct', to='caregivers.caregiverprofile')),
            ],
            options={
                'ordering': ['-signed_at'],
            },
        ),
        
        # Training Module
        migrations.CreateModel(
            name='TrainingModule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('content', models.TextField(help_text='Full training content')),
                ('order', models.PositiveIntegerField(default=0, help_text='Display order')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['order', 'created_at'],
            },
        ),
        
        # Training Quiz
        migrations.CreateModel(
            name='TrainingQuiz',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField()),
                ('option_a', models.CharField(max_length=255)),
                ('option_b', models.CharField(max_length=255)),
                ('option_c', models.CharField(blank=True, max_length=255)),
                ('option_d', models.CharField(blank=True, max_length=255)),
                ('correct_answer', models.CharField(choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], max_length=1)),
                ('order', models.PositiveIntegerField(default=0)),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='caregivers.trainingmodule')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        
        # Training Completion
        migrations.CreateModel(
            name='TrainingCompletion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('passed', models.BooleanField(default=False)),
                ('score', models.PositiveIntegerField(default=0)),
                ('total_questions', models.PositiveIntegerField(default=0)),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('caregiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='training_completions', to='caregivers.caregiverprofile')),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='completions', to='caregivers.trainingmodule')),
            ],
            options={
                'ordering': ['-completed_at'],
                'unique_together': {('caregiver', 'module')},
            },
        ),
        
        # Earnings Wallet
        migrations.CreateModel(
            name='EarningsWallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('description', models.CharField(max_length=255)),
                ('payout_status', models.CharField(choices=[('pending', 'Pending (24-hour security window)'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('caregiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='earnings', to='caregivers.caregiverprofile')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
