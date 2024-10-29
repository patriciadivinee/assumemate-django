# Generated by Django 5.1.1 on 2024-10-20 12:55

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0010_alter_chatmessage_chatmess_content'),
    ]

    operations = [
        migrations.CreateModel(
            name='ListingApplication',
            fields=[
                ('list_app_id', models.AutoField(primary_key=True, serialize=False)),
                ('list_app_status', models.CharField(max_length=20)),
                ('list_app_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('list_reason', models.CharField(max_length=255, null=True)),
                ('list_app_reviewer_id', models.ForeignKey(blank=True, db_column='user_app_reviewer_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='listing_reviews', to=settings.AUTH_USER_MODEL)),
                ('list_id', models.ForeignKey(db_column='list_id', on_delete=django.db.models.deletion.CASCADE, to='base.listing')),
                ('user_id', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.CASCADE, related_name='listing_applications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'listing_application',
            },
        ),
        migrations.CreateModel(
            name='PromoteListing',
            fields=[
                ('prom_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('prom_start', models.DateTimeField()),
                ('prom_end', models.DateTimeField()),
                ('list_id', models.ForeignKey(db_column='list_id', on_delete=django.db.models.deletion.CASCADE, to='base.listing')),
            ],
            options={
                'db_table': 'promote_listing',
            },
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('report_id', models.AutoField(primary_key=True, serialize=False)),
                ('report_details', models.JSONField(null=True)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('report_status', models.CharField(default='PENDING', max_length=20)),
                ('report_reason', models.CharField(max_length=255, null=True)),
                ('reviewer', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.CASCADE, related_name='reviewed_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'report',
            },
        ),
        migrations.CreateModel(
            name='SuspendedUser',
            fields=[
                ('sus_id', models.AutoField(primary_key=True, serialize=False)),
                ('sus_start', models.DateTimeField(auto_now_add=True)),
                ('sus_end', models.DateTimeField()),
                ('user_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
