# Generated by Django 3.0.8 on 2020-08-11 07:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lockdownsf', '0010_auto_20200808_2118'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tag',
            name='media_items',
        ),
        migrations.AddField(
            model_name='mediaitem',
            name='tags',
            field=models.ManyToManyField(to='lockdownsf.Tag'),
        ),
    ]
