# Generated by Django 3.0.8 on 2020-08-21 06:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lockdownsf', '0013_auto_20200820_1539'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mediaitem',
            name='album',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='lockdownsf.Album'),
        ),
    ]
