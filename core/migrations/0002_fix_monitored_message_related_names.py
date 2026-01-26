# Generated migration to fix related_name conflicts

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('families', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        # Update sender related_name
        migrations.AlterField(
            model_name='monitoredmessage',
            name='sender',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sent_monitored_messages',
                to='accounts.user'
            ),
        ),
        # Update recipient related_name
        migrations.AlterField(
            model_name='monitoredmessage',
            name='recipient',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='received_monitored_messages',
                to='accounts.user'
            ),
        ),
        # Update booking related_name
        migrations.AlterField(
            model_name='monitoredmessage',
            name='booking',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='monitored_messages',
                to='families.booking'
            ),
        ),
    ]
