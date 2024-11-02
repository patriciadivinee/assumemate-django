# Generated by Django 5.1.1 on 2024-10-29 15:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0015_alter_passwordresettoken_reset_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='passwordresettoken',
            name='reset_token',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='passwordresettoken',
            name='reset_token_created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='passwordresettoken',
            name='reset_token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
