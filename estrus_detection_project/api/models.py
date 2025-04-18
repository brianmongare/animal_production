from django.db import models
from django.utils import timezone

class AnimalBreed(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class Animal(models.Model):
    ESTRUS_STATUS_CHOICES = [
        ('normal', 'Normal'),
        ('pre-estrus', 'Pre-Estrus'),
        ('estrus', 'Estrus'),
    ]
    
    animal_id = models.CharField(max_length=50, unique=True)
    breed = models.ForeignKey(AnimalBreed, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True)
    number = models.PositiveIntegerField()
    date_registered = models.DateTimeField(default=timezone.now)
    is_pregnant = models.BooleanField(default=False)
    current_status = models.CharField(max_length=20, choices=ESTRUS_STATUS_CHOICES, default='normal')
    status_since = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.breed.name} #{self.number}"
    
    def save(self, *args, **kwargs):
        # If status changes, update status_since timestamp
        if self.pk:
            orig = Animal.objects.get(pk=self.pk)
            if orig.current_status != self.current_status:
                self.status_since = timezone.now()
        else:
            # For new animals
            self.status_since = timezone.now()
            
        super().save(*args, **kwargs)

class Device(models.Model):
    device_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    animal = models.OneToOneField(Animal, on_delete=models.SET_NULL, null=True, blank=True, related_name='device')
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    battery_level = models.IntegerField(default=100)
    
    def __str__(self):
        return self.name

class ActivityReading(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name='activity_readings')
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    activity_level = models.IntegerField(help_text="Activity level in percentage (0-100)")
    temperature = models.DecimalField(max_digits=4, decimal_places=1, help_text="Temperature in Celsius")
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.animal} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

class EstrusEvent(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name='estrus_events')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    was_inseminated = models.BooleanField(default=False)
    insemination_time = models.DateTimeField(null=True, blank=True)
    resulted_in_pregnancy = models.BooleanField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.animal} - {self.start_time.strftime('%Y-%m-%d')}"

class Alert(models.Model):
    ALERT_TYPES = [
        ('estrus', 'Estrus Detected'),
        ('pre-estrus', 'Pre-Estrus Detected'),
        ('health', 'Health Concern'),
        ('device', 'Device Issue'),
    ]
    
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    timestamp = models.DateTimeField(default=timezone.now)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.animal}"
