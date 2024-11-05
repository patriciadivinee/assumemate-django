# Generated by Django 5.1.1 on 2024-11-05 01:59

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0002_remove_listingapplication_user_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('user_id', models.OneToOneField(db_column='user_id', editable=False, on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('wall_amnt', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
            options={
                'db_table': 'wallet',
            },
        ),
    ]
