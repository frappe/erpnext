"""
Login and logout views for the browsable API.

Add these to your root URLconf if you're using the browsable API and
your API requires authentication:

    urlpatterns = [
        ...
        path('auth/', include('rest_framework.urls'))
    ]

You should make sure your authentication settings include `SessionAuthentication`.
"""
from django.contrib.auth import views
from django.urls import path

app_name = 'rest_framework'
urlpatterns = [
    path('login/', views.LoginView.as_view(template_name='rest_framework/login.html'), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]
