# Generated by Django 5.1.1 on 2024-11-17 16:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0007_transaction_transaction_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='transaction_status',
        ),
    ]
