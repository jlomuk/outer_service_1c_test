from django.contrib import admin
from django.template.defaulttags import url
from django.urls import path, include

urlpatterns = [
    path('healthz/', include('health_check.urls')),
    path('admin/', admin.site.urls),
    path('team/', include('employees.urls'))
]