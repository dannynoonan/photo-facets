from django.db import models


class Neighborhood(models.Model):
    slug = models.SlugField(max_length=32, primary_key=True)
    name = models.CharField(max_length=64)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)

    def __str__(self):
        return self.slug

class Photo(models.Model):
    file_name = models.CharField(max_length=64, db_index=True)
    neighborhood_slug = models.ForeignKey(Neighborhood, db_column='neighborhood_slug', on_delete=models.CASCADE)
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
    other_types = models.CharField(max_length=128, null=True)
    
    class Meta:
        unique_together = ('file_name', 'neighborhood_slug')
    
    def __str__(self):
        return self.neighborhood_slug.slug + '/' + self.file_name + '.' + self.file_format