from django.urls import path

from cars.admin_panel import views

app_name = 'admin_panel'

urlpatterns = [
    path('login/', views.StaffLoginView.as_view(), name='login'),
    path('logout/', views.StaffLogoutView.as_view(), name='logout'),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('users/', views.CustomerUserListView.as_view(), name='user_list'),
    path('wishlist/', views.WishlistActivityListView.as_view(), name='wishlist_list'),
    path(
        'sell-car-inquiries/',
        views.SellCarInquiryListView.as_view(),
        name='sell_car_inquiry_list',
    ),
    path(
        'sell-car-inquiries/bulk-delete/',
        views.SellCarInquiryBulkDeleteView.as_view(),
        name='sell_car_inquiry_bulk_delete',
    ),
    path(
        'sell-car-inquiries/<int:pk>/approve/',
        views.SellCarInquiryApproveView.as_view(),
        name='sell_car_inquiry_approve',
    ),
    path(
        'sell-car-inquiries/<int:pk>/toggle-featured/',
        views.SellCarInquiryToggleFeaturedView.as_view(),
        name='sell_car_inquiry_toggle_featured',
    ),
    path('cars/', views.CarListView.as_view(), name='car_list'),
    path('cars/add/', views.CarCreateView.as_view(), name='car_add'),
    path('cars/<int:pk>/edit/', views.CarUpdateView.as_view(), name='car_edit'),
    path('cars/<int:pk>/delete/', views.CarDeleteView.as_view(), name='car_delete'),
    path('cars/bulk-delete/', views.CarBulkDeleteView.as_view(), name='car_bulk_delete'),
    path('api/brands/<int:pk>/models/', views.BrandModelsJsonView.as_view(), name='api_brand_models'),
    path('api/inquiries/unread-count/', views.UnreadInquiryCountJsonView.as_view(), name='api_unread_count'),
    path('brands/', views.BrandListView.as_view(), name='brand_list'),
    path('brands/bulk-add/', views.BrandBulkAddView.as_view(), name='brand_bulk_add'),
    path('brands/add/', views.BrandCreateView.as_view(), name='brand_add'),
    path('brands/<int:pk>/delete-all-models/', views.BrandDeleteAllModelsView.as_view(), name='brand_delete_all_models'),
    path('brands/<int:pk>/edit/', views.BrandUpdateView.as_view(), name='brand_edit'),
    path('brands/<int:pk>/delete/', views.BrandDeleteView.as_view(), name='brand_delete'),
    path('carmodels/', views.CarModelListView.as_view(), name='carmodel_list'),
    path('carmodels/bulk-add/', views.CarModelBulkAddView.as_view(), name='carmodel_bulk_add'),
    path('carmodels/add/', views.CarModelCreateView.as_view(), name='carmodel_add'),
    path('carmodels/<int:pk>/edit/', views.CarModelUpdateView.as_view(), name='carmodel_edit'),
    path('carmodels/<int:pk>/delete/', views.CarModelDeleteView.as_view(), name='carmodel_delete'),
    path('inquiries/', views.InquiryListView.as_view(), name='inquiry_list'),
    path('inquiries/mark-all-read/', views.InquiryMarkAllReadView.as_view(), name='inquiry_mark_all_read'),
    path('inquiries/<int:pk>/mark-read/', views.InquiryMarkReadView.as_view(), name='inquiry_mark_read'),
    path('inquiries/<int:pk>/delete/', views.InquiryDeleteView.as_view(), name='inquiry_delete'),
    path('inquiries/<int:pk>/', views.InquiryDetailView.as_view(), name='inquiry_detail'),
    path('csv/import/', views.CSVImportView.as_view(), name='csv_import'),
    path('csv/preview/', views.CSVPreviewView.as_view(), name='csv_preview'),
    path('csv/confirm/', views.CSVConfirmView.as_view(), name='csv_confirm'),
    path('csv/export/', views.CSVExportView.as_view(), name='csv_export'),
]
