from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("families", "0001_initial"),
        ("caregivers", "0007_new_features"),
    ]

    operations = [
        migrations.AddField(
            model_name="familyprofile",
            name="default_payment_provider",
            field=models.CharField(
                blank=True,
                help_text="Preferred provider: paystack/flutterwave/opay/moniepoint",
                max_length=50,
            ),
        ),
        migrations.CreateModel(
            name="AuthorizedPickup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=255)),
                ("relationship", models.CharField(blank=True, max_length=100)),
                ("photo", models.ImageField(blank=True, null=True, upload_to="authorized_pickups/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "family",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="authorized_pickups",
                        to="families.familyprofile",
                    ),
                ),
            ],
            options={"ordering": ["full_name"]},
        ),
        migrations.CreateModel(
            name="IncidentReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "incident_type",
                    models.CharField(
                        choices=[
                            ("late_arrival", "Late Arrival"),
                            ("theft_suspicion", "Theft Suspicion"),
                            ("misconduct", "Misconduct"),
                        ],
                        max_length=50,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved", models.BooleanField(default=False)),
                (
                    "caregiver",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="incidents",
                        to="caregivers.caregiverprofile",
                    ),
                ),
                (
                    "family",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incidents",
                        to="families.familyprofile",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Booking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "payment_provider",
                    models.CharField(
                        choices=[
                            ("paystack", "Paystack"),
                            ("flutterwave", "Flutterwave"),
                            ("opay", "Opay"),
                            ("moniepoint", "Moniepoint"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "provider_reference",
                    models.CharField(
                        blank=True, help_text="Gateway reference / transaction ID", max_length=255
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending Payment"),
                            ("escrow", "In Escrow"),
                            ("released", "Released to Nanny"),
                            ("refunded", "Refunded"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("service_date", models.DateField(blank=True, null=True)),
                (
                    "agent_commission",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Platform/agent fee",
                        max_digits=10,
                    ),
                ),
                (
                    "caregiver_payout",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Net payout to caregiver",
                        max_digits=10,
                    ),
                ),
                (
                    "caregiver",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to="caregivers.caregiverprofile",
                    ),
                ),
                (
                    "family",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to="families.familyprofile",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

