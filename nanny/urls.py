from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication via Allauth (login/logout)
    path('accounts/', include('allauth.urls')),  # /accounts/login/, /accounts/logout/

    # Custom signup pages
    path('signup/', include('accounts.urls')),  # /signup/family/, /signup/caregiver/

    # Other apps
    path('caregivers/', include('caregivers.urls')),
    path('families/', include('families.urls')),
    path('messages/', include('messaging.urls')),
    path('core/', include('core.urls')),  # Admin actions

    # Home page (core app)
    path('', include('core.urls')),  # '/' goes to home page
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
