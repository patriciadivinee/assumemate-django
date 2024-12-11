# Generated by Django 5.1.1 on 2024-12-09 17:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='refundrequest',
            name='refund_status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('REFUNDED', 'Approved')], default='PENDING', max_length=15),
        ),
    ]
