from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('', views.home, name='home'),
    path('cars/', views.car_list, name='car_list'),
    path('cars/<int:pk>/', views.car_detail, name='car_detail'),
    path('contact/', views.contact, name='contact'),
    path('sell/', views.sell_car, name='sell_car'),
    path('api/models/', views.get_models, name='api_get_models'),
    path('api/variants/', views.get_variants, name='api_get_variants'),
    path('api/home-cars/', views.home_cars_api, name='api_home_cars'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('dashboard/sell/', views.sell_requests_dashboard, name='sell_requests_dashboard'),
    path('wishlist/toggle/<int:pk>/', views.toggle_wishlist, name='toggle_wishlist'),
]
