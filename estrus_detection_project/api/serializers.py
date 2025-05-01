from rest_framework import serializers
from .models import AnimalBreed, Animal, Device, ActivityReading, EstrusEvent, Alert
from django.utils import timezone


class AnimalBreedSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalBreed
        fields = '__all__'

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'

class ActivityReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityReading
        fields = '__all__'
        
class ActivityReadingDetailSerializer(serializers.ModelSerializer):
    animal_name = serializers.StringRelatedField(source='animal')
    
    class Meta:
        model = ActivityReading
        fields = ['id', 'animal', 'animal_name', 'timestamp', 'activity_level', 'temperature']

class EstrusEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstrusEvent
        fields = '__all__'

class AlertSerializer(serializers.ModelSerializer):
    animal_name = serializers.StringRelatedField(source='animal')
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    
    class Meta:
        model = Alert
        fields = ['id', 'animal', 'animal_name', 'alert_type', 'alert_type_display', 
                 'timestamp', 'message', 'is_resolved', 'resolved_at']

class AnimalSerializer(serializers.ModelSerializer):
    breed_name = serializers.StringRelatedField(source='breed')
    status_since_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = Animal
        fields = ['id', 'animal_id', 'breed', 'breed_name', 'name', 'number', 
                 'date_registered', 'is_pregnant', 'current_status', 
                 'status_since', 'status_since_hours', 'notes']
    
    def get_status_since_hours(self, obj):
        if obj.status_since:
            time_diff = timezone.now() - obj.status_since
            return round(time_diff.total_seconds() / 3600)
        return None

class AnimalDetailSerializer(AnimalSerializer):
    device = DeviceSerializer(read_only=True)
    recent_activities = serializers.SerializerMethodField()
    active_alerts = serializers.SerializerMethodField()
    
    class Meta(AnimalSerializer.Meta):
        fields = AnimalSerializer.Meta.fields + ['device', 'recent_activities', 'active_alerts']
    
    def get_recent_activities(self, obj):
        activities = obj.activity_readings.all()[:10]
        return ActivityReadingSerializer(activities, many=True).data
    
    def get_active_alerts(self, obj):
        alerts = obj.alerts.filter(is_resolved=False)
        return AlertSerializer(alerts, many=True).data

class DashboardStatsSerializer(serializers.Serializer):
    total_animals = serializers.IntegerField()
    in_estrus = serializers.IntegerField()
    pre_estrus = serializers.IntegerField()
    pregnancy_rate = serializers.FloatField()
    active_alerts = serializers.IntegerField()