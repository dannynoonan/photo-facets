from django.contrib.postgres.fields import ArrayField
from django.db import models


class User(models.Model):
    email = models.CharField(max_length=512, db_index=True, unique=True)
    dt_inserted = models.DateTimeField(auto_now_add=True)
    dt_last_login = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=64, db_index=True)

    def __str__(self):
        return self.email

    
class Tag(models.Model):
    name = models.CharField(max_length=256, db_index=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    dt_inserted = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=64, db_index=True)

    class Meta:
        unique_together = ('name', 'owner')

    def __str__(self):
        return self.name


class Album(models.Model):
    s3_dir = models.CharField(max_length=128, db_index=True, unique=True) 
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=500)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    map_zoom_level = models.IntegerField(default=0)
    photos_having_gps = models.IntegerField(default=0)
    dt_inserted = models.DateTimeField(auto_now_add=True)
    dt_updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=64, db_index=True)

    def __str__(self):
        return f"{self.id}:{self.name}"


class Photo(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=256, db_index=True)
    mime_type = models.CharField(max_length=128, db_index=True)
    description = models.CharField(max_length=500, null=True)
    width = models.IntegerField(null=True)
    height = models.IntegerField(null=True)
    dt_taken = models.DateTimeField(null=True)
    dt_inserted = models.DateTimeField(auto_now_add=True)
    dt_updated = models.DateTimeField(auto_now=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    tags = models.ManyToManyField(Tag)
    extracted_text_search = models.CharField(max_length=16000, null=True)
    extracted_text_display = models.CharField(max_length=16000, null=True)
    status = models.CharField(max_length=64, db_index=True)

    class Meta:
        unique_together = ('album', 'file_name')

    def __str__(self):
        return f"{self.id}:{self.file_name}"  
    