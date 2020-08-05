from django.db import models


class Neighborhood(models.Model):
    slug = models.SlugField(max_length=32, db_index=True, unique=True)
    name = models.CharField(max_length=64)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    dt_inserted = models.DateTimeField(auto_now_add=True)
    dt_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.slug

class Photo(models.Model):
    uuid = models.CharField(max_length=36, db_index=True, primary_key=True)
    source_file_name = models.CharField(max_length=64, db_index=True)
    neighborhood = models.ForeignKey(Neighborhood, on_delete=models.CASCADE)
    file_format = models.CharField(max_length=8, db_index=True)
    dt_taken = models.DateTimeField(null=True)
    dt_inserted = models.DateTimeField(auto_now_add=True)
    dt_updated = models.DateTimeField(auto_now=True)
    width_pixels = models.IntegerField(default=0)
    height_pixels = models.IntegerField(default=0)
    aspect_format = models.CharField(max_length=16, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    scene_type = models.CharField(max_length=32, db_index=True)
    business_type = models.CharField(max_length=32, db_index=True, null=True)
    other_labels = models.CharField(max_length=128, null=True)
    extracted_text_raw = models.CharField(max_length=4096, null=True)
    extracted_text_formatted = models.CharField(max_length=4096, null=True)
    
    def __str__(self):
        return self.uuid + ' (' + self.neighborhood.slug + ' / ' + self.source_file_name + ')'


class Album(models.Model):
    external_id = models.CharField(max_length=500, db_index=True)
    external_resource = models.CharField(max_length=64, db_index=True, null=True)
    name = models.CharField(max_length=500)
    description = models.CharField(max_length=500)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    dt_inserted = models.DateTimeField(auto_now_add=True)
    dt_updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=64, db_index=True)

    def __str__(self):
        return f"{self.name}|{self.external_resource}|{self.external_id}|{self.status}"


class MediaItem(models.Model):
    external_id = models.CharField(max_length=500, db_index=True, null=True)
    external_resource = models.CharField(max_length=64, db_index=True, null=True)
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=64, db_index=True)
    mime_type = models.CharField(max_length=128, db_index=True)
    description = models.CharField(max_length=500)
    dt_taken = models.DateTimeField(null=True)
    dt_inserted = models.DateTimeField(auto_now_add=True)
    dt_updated = models.DateTimeField(auto_now=True)
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    facets = models.CharField(max_length=1024, null=True)
    extracted_text = models.CharField(max_length=4096, null=True)
    status = models.CharField(max_length=64, db_index=True)

    def __str__(self):
        return f"{self.file_name}|{self.mime_type}|{self.external_resource}|{self.external_id}|{self.status}"
    