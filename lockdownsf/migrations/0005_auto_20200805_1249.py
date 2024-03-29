# Generated by Django 3.0.8 on 2020-08-05 19:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lockdownsf', '0004_album_mediaitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='album',
            name='map_zoom_level',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='album',
            name='description',
            field=models.CharField(max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='album',
            name='external_id',
            field=models.CharField(db_index=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='mediaitem',
            name='description',
            field=models.CharField(max_length=500, null=True),
        ),
    ]
