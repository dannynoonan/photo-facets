# Generated by Django 3.0.8 on 2020-08-30 08:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lockdownsf', '0016_remove_album_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='photo',
            name='neighborhood',
        ),
        migrations.DeleteModel(
            name='Neighborhood',
        ),
        migrations.DeleteModel(
            name='Photo',
        ),
    ]
