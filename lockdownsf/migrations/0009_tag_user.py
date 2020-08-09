# Generated by Django 3.0.8 on 2020-08-09 04:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lockdownsf', '0008_auto_20200808_1642'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.CharField(db_index=True, max_length=512)),
                ('dt_inserted', models.DateTimeField(auto_now_add=True)),
                ('dt_last_login', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(db_index=True, max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=256)),
                ('dt_inserted', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(db_index=True, max_length=64)),
                ('media_items', models.ManyToManyField(to='lockdownsf.MediaItem')),
            ],
        ),
    ]
