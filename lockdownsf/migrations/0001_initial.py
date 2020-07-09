# Generated by Django 3.0.8 on 2020-07-09 06:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Neighborhood',
            fields=[
                ('slug', models.SlugField(max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64)),
                ('center_latitude', models.DecimalField(decimal_places=6, max_digits=9, null=True)),
                ('center_longitude', models.DecimalField(decimal_places=6, max_digits=9, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Photo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(db_index=True, max_length=64)),
                ('file_format', models.CharField(db_index=True, max_length=8)),
                ('dt_taken', models.DateTimeField(null=True)),
                ('dt_inserted', models.DateTimeField(auto_now_add=True)),
                ('dt_updated', models.DateTimeField(auto_now=True)),
                ('width_pixels', models.IntegerField(default=0)),
                ('height_pixels', models.IntegerField(default=0)),
                ('aspect_format', models.CharField(db_index=True, max_length=16)),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9, null=True)),
                ('scene_type', models.CharField(db_index=True, max_length=32)),
                ('business_type', models.CharField(db_index=True, max_length=32, null=True)),
                ('other_types', models.CharField(max_length=128, null=True)),
                ('neighborhood_slug', models.ForeignKey(db_column='neighborhood_slug', on_delete=django.db.models.deletion.CASCADE, to='lockdownsf.Neighborhood')),
            ],
            options={
                'unique_together': {('file_name', 'neighborhood_slug')},
            },
        ),
    ]
