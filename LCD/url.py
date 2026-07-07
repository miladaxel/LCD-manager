from django.urls import path
from LCD import views

app_name = 'LCD'


urlpatterns = [
    path('lcd/<slug:slug>', views.LCDDetailView.as_view(), name='lcd_detail'),
    path('', views.LCDListView.as_view(), name='lcd_list'),
    path('create/', views.LCDCreateView.as_view(), name='lcd_create'),
    path('<slug:slug>/update/', views.LCDUpdateView.as_view(), name='lcd_update'),
    path('<slug:slug>/delete/', views.LCDDeleteView.as_view(), name='lcd_delete'),
    path('brands/', views.BrandListView.as_view(), name='brand_list'),
    path('brand/<slug:slug>/', views.BrandDetailView.as_view(), name='brand_detail'),


]