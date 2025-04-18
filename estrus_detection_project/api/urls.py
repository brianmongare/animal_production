from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AnimalBreedViewSet, AnimalViewSet, DeviceViewSet, 
    ActivityReadingViewSet, EstrusEventViewSet, AlertViewSet,
    dashboard_stats, activity_chart_data
)

router = DefaultRouter()
router.register(r'breeds', AnimalBreedViewSet)
router.register(r'animals', AnimalViewSet)
router.register(r'devices', DeviceViewSet)
router.register(r'activity', ActivityReadingViewSet)
router.register(r'estrus-events', EstrusEventViewSet)
router.register(r'alerts', AlertViewSet)



urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    path('dashboard/activity-chart/', activity_chart_data, name='activity-chart-data'),
]
