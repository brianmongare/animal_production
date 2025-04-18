from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

from .models import AnimalBreed, Animal, Device, ActivityReading, EstrusEvent, Alert
from .serializers import (
    AnimalBreedSerializer, AnimalSerializer, AnimalDetailSerializer,
    DeviceSerializer, ActivityReadingSerializer, ActivityReadingDetailSerializer,
    EstrusEventSerializer, AlertSerializer, DashboardStatsSerializer
)

class AnimalBreedViewSet(viewsets.ModelViewSet):
    queryset = AnimalBreed.objects.all()
    serializer_class = AnimalBreedSerializer

class AnimalViewSet(viewsets.ModelViewSet):
    queryset = Animal.objects.all()
    serializer_class = AnimalSerializer
    filterset_fields = ['breed', 'current_status', 'is_pregnant']
    search_fields = ['animal_id', 'name', 'number']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AnimalDetailSerializer
        return AnimalSerializer
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        status_param = request.query_params.get('status', None)
        if status_param:
            animals = Animal.objects.filter(current_status=status_param)
            serializer = self.get_serializer(animals, many=True)
            return Response(serializer.data)
        return Response({"error": "Status parameter required"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def activity_history(self, request, pk=None):
        animal = self.get_object()
        days = int(request.query_params.get('days', 1))
        since = timezone.now() - timedelta(days=days)
        
        readings = ActivityReading.objects.filter(
            animal=animal,
            timestamp__gte=since
        ).order_by('timestamp')
        
        serializer = ActivityReadingSerializer(readings, many=True)
        return Response(serializer.data)

class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    filterset_fields = ['is_active']
    search_fields = ['device_id', 'name']
    
    @action(detail=True, methods=['post'])
    def assign_to_animal(self, request, pk=None):
        device = self.get_object()
        animal_id = request.data.get('animal_id')
        
        try:
            animal = Animal.objects.get(id=animal_id)
            device.animal = animal
            device.save()
            return Response({"status": "Device assigned successfully"})
        except Animal.DoesNotExist:
            return Response(
                {"error": "Animal not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

class ActivityReadingViewSet(viewsets.ModelViewSet):
    queryset = ActivityReading.objects.all()
    serializer_class = ActivityReadingSerializer
    
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ActivityReadingDetailSerializer
        return ActivityReadingSerializer
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        
        readings = ActivityReading.objects.filter(
            timestamp__gte=since
        ).select_related('animal').order_by('-timestamp')
        
        serializer = ActivityReadingDetailSerializer(readings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        readings = request.data
        serializer = ActivityReadingSerializer(data=readings, many=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # Automatic status update based on new readings
            self._update_animal_statuses(readings)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _update_animal_statuses(self, readings):
        """
        Update animal statuses based on new activity readings
        This is a simplified example - in a real system you'd have more 
        sophisticated algorithms to detect estrus
        """
        # Group readings by animal
        animal_readings = {}
        for reading in readings:
            animal_id = reading.get('animal')
            if animal_id not in animal_readings:
                animal_readings[animal_id] = []
            animal_readings[animal_id].append(reading)
        
        # Check each animal's readings for signs of estrus
        for animal_id, animal_data in animal_readings.items():
            try:
                animal = Animal.objects.get(id=animal_id)
                
                # Calculate average activity level and temperature
                avg_activity = sum(r['activity_level'] for r in animal_data) / len(animal_data)
                avg_temp = sum(float(r['temperature']) for r in animal_data) / len(animal_data)
                
                # Simple rule-based detection (would be more sophisticated in production)
                if avg_activity > 80 and avg_temp > 38.5:
                    new_status = 'estrus'
                elif avg_activity > 60 and avg_temp > 38.2:
                    new_status = 'pre-estrus'
                else:
                    new_status = 'normal'
                
                # If status changed, update and create alert
                if animal.current_status != new_status:
                    animal.current_status = new_status
                    animal.save()
                    
                    if new_status in ['estrus', 'pre-estrus']:
                        Alert.objects.create(
                            animal=animal,
                            alert_type=new_status,
                            message=f"{new_status.capitalize()} detected for {animal}",
                        )
                        
            except Animal.DoesNotExist:
                continue

class EstrusEventViewSet(viewsets.ModelViewSet):
    queryset = EstrusEvent.objects.all()
    serializer_class = EstrusEventSerializer
    
    @action(detail=True, methods=['post'])
    def record_insemination(self, request, pk=None):
        event = self.get_object()
        event.was_inseminated = True
        event.insemination_time = timezone.now()
        event.save()
        
        return Response({"status": "Insemination recorded"})
    
    @action(detail=True, methods=['post'])
    def record_pregnancy(self, request, pk=None):
        event = self.get_object()
        is_pregnant = request.data.get('is_pregnant', True)
        
        event.resulted_in_pregnancy = is_pregnant
        event.save()
        
        # Update animal pregnancy status
        animal = event.animal
        animal.is_pregnant = is_pregnant
        animal.save()
        
        return Response({"status": "Pregnancy status updated"})

class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    filterset_fields = ['animal', 'alert_type', 'is_resolved']
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        
        return Response({"status": "Alert marked as resolved"})
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        alerts = Alert.objects.filter(is_resolved=False).select_related('animal')
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)

@api_view(['GET'])
def dashboard_stats(request):
    """Get dashboard statistics"""
    # Get counts
    total_animals = Animal.objects.count()
    in_estrus = Animal.objects.filter(current_status='estrus').count()
    pre_estrus = Animal.objects.filter(current_status='pre-estrus').count()
    
    # Calculate pregnancy rate
    pregnancies = Animal.objects.filter(is_pregnant=True).count()
    pregnancy_rate = (pregnancies / total_animals) * 100 if total_animals > 0 else 0
    
    # Count active alerts
    active_alerts = Alert.objects.filter(is_resolved=False).count()
    
    stats = {
        'total_animals': total_animals,
        'in_estrus': in_estrus,
        'pre_estrus': pre_estrus,
        'pregnancy_rate': round(pregnancy_rate, 1),
        'active_alerts': active_alerts
    }
    
    serializer = DashboardStatsSerializer(stats)
    return Response(serializer.data)

@api_view(['GET'])
def activity_chart_data(request):
    """Get activity chart data for dashboard"""
    hours = int(request.query_params.get('hours', 24))
    since = timezone.now() - timedelta(hours=hours)
    
    # Create time intervals (e.g., hourly buckets)
    time_intervals = []
    current = since
    while current <= timezone.now():
        time_intervals.append({
            'start': current,
            'end': current + timedelta(hours=2),  # 2-hour intervals
            'label': current.strftime('%H:%00')
        })
        current += timedelta(hours=2)
    
    # Get average activity by status and time interval
    result = []
    for interval in time_intervals:
        # Get activity averages for each status group
        estrus_avg = ActivityReading.objects.filter(
            animal__current_status='estrus',
            timestamp__gte=interval['start'],
            timestamp__lt=interval['end']
        ).aggregate(avg=Avg('activity_level'))
        
        pre_estrus_avg = ActivityReading.objects.filter(
            animal__current_status='pre-estrus',
            timestamp__gte=interval['start'],
            timestamp__lt=interval['end']
        ).aggregate(avg=Avg('activity_level'))
        
        normal_avg = ActivityReading.objects.filter(
            animal__current_status='normal',
            timestamp__gte=interval['start'],
            timestamp__lt=interval['end']
        ).aggregate(avg=Avg('activity_level'))
        
        result.append({
            'time': interval['label'],
            'estrus': estrus_avg['avg'] if estrus_avg['avg'] else 0,
            'pre_estrus': pre_estrus_avg['avg'] if pre_estrus_avg['avg'] else 0,
            'normal': normal_avg['avg'] if normal_avg['avg'] else 0
        })
    
    return Response(result)
