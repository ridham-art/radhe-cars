from django.urls import path
from django.views.generic import RedirectView

from cars.admin_panel import views

app_name = 'admin_panel'

urlpatterns = [
    path('login/', views.StaffLoginView.as_view(), name='login'),
    path('logout/', views.StaffLogoutView.as_view(), name='logout'),
    path('', views.DashboardPreviewView.as_view(), name='dashboard'),
    path('customers/', views.CustomerListPreviewView.as_view(), name='customer_list'),
    path('wishlists/', views.WishlistListPreviewView.as_view(), name='wishlist_list'),
    path(
        'sell-car-inquiries/',
        views.SellCarInquiryPreviewView.as_view(),
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
        'sell-car-inquiries/<int:pk>/reject/',
        views.SellCarInquiryRejectView.as_view(),
        name='sell_car_inquiry_reject',
    ),
    path(
        'sell-car-inquiries/<int:pk>/toggle-featured/',
        views.SellCarInquiryToggleFeaturedView.as_view(),
        name='sell_car_inquiry_toggle_featured',
    ),
    path('cars/', views.CarListPreviewView.as_view(), name='car_list'),
    path(
        'vehicle-master/',
        views.VehicleMasterPreviewView.as_view(),
        name='vehicle_master',
    ),
    path(
        'vehicle-master/makes/add/',
        views.VehicleMasterMakeAddView.as_view(),
        name='vehicle_master_make_add',
    ),
    path(
        'vehicle-master/makes/<int:pk>/edit/',
        views.VehicleMasterMakeEditView.as_view(),
        name='vehicle_master_make_edit',
    ),
    path(
        'vehicle-master/makes/<int:pk>/delete/',
        views.VehicleMasterMakeDeleteView.as_view(),
        name='vehicle_master_make_delete',
    ),
    path(
        'vehicle-master/makes/bulk-add/',
        views.VehicleMasterMakeBulkAddView.as_view(),
        name='vehicle_master_make_bulk_add',
    ),
    path(
        'vehicle-master/makes/bulk-delete/',
        views.VehicleMasterMakeBulkDeleteView.as_view(),
        name='vehicle_master_make_bulk_delete',
    ),
    path(
        'vehicle-master/models/add/',
        views.VehicleMasterModelAddView.as_view(),
        name='vehicle_master_model_add',
    ),
    path(
        'vehicle-master/models/<int:pk>/edit/',
        views.VehicleMasterModelEditView.as_view(),
        name='vehicle_master_model_edit',
    ),
    path(
        'vehicle-master/models/<int:pk>/delete/',
        views.VehicleMasterModelDeleteView.as_view(),
        name='vehicle_master_model_delete',
    ),
    path(
        'vehicle-master/models/bulk-add/',
        views.VehicleMasterModelBulkAddView.as_view(),
        name='vehicle_master_model_bulk_add',
    ),
    path(
        'vehicle-master/models/bulk-delete/',
        views.VehicleMasterModelBulkDeleteView.as_view(),
        name='vehicle_master_model_bulk_delete',
    ),
    path(
        'vehicle-master/variants/add/',
        views.VehicleMasterVariantAddView.as_view(),
        name='vehicle_master_variant_add',
    ),
    path(
        'vehicle-master/variants/bulk-add/',
        views.VehicleMasterVariantBulkAddView.as_view(),
        name='vehicle_master_variant_bulk_add',
    ),
    path(
        'vehicle-master/variants/bulk-delete/',
        views.VehicleMasterVariantBulkDeleteView.as_view(),
        name='vehicle_master_variant_bulk_delete',
    ),
    path(
        'vehicle-master/variants/<int:pk>/edit/',
        views.VehicleMasterVariantEditView.as_view(),
        name='vehicle_master_variant_edit',
    ),
    path(
        'vehicle-master/variants/<int:pk>/delete/',
        views.VehicleMasterVariantDeleteView.as_view(),
        name='vehicle_master_variant_delete',
    ),
    path('cars/export/csv/', views.CarListCSVExportView.as_view(), name='car_list_csv'),
    path('cars/add/', views.CarCreatePreviewView.as_view(), name='car_add'),
    path('cars/<int:pk>/edit/', views.CarUpdatePreviewView.as_view(), name='car_edit'),
    path(
        'cars/<int:car_pk>/images/<int:image_pk>/delete/',
        views.CarImageDeleteView.as_view(),
        name='car_image_delete',
    ),
    path(
        'cars/<int:car_pk>/images/delete-all/',
        views.CarImageDeleteAllView.as_view(),
        name='car_image_delete_all',
    ),
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
    path('inquiries/', views.InquiryListPreviewView.as_view(), name='inquiry_list'),
    path(
        'inquiries/<int:pk>/',
        views.InquiryDetailPreviewView.as_view(),
        name='inquiry_detail',
    ),
    path('inquiries/mark-all-read/', views.InquiryMarkAllReadView.as_view(), name='inquiry_mark_all_read'),
    path('inquiries/<int:pk>/mark-read/', views.InquiryMarkReadView.as_view(), name='inquiry_mark_read'),
    path('inquiries/<int:pk>/delete/', views.InquiryDeleteView.as_view(), name='inquiry_delete'),
    path('csv/import/', views.CSVImportPreviewView.as_view(), name='csv_import'),
    path('csv/preview/', views.CSVPreviewPreviewView.as_view(), name='csv_preview'),
    path('csv/confirm/', views.CSVConfirmView.as_view(), name='csv_confirm'),
    path('csv/export/', views.CSVExportView.as_view(), name='csv_export'),
    # Legacy preview URL aliases (bookmarks)
    path(
        'ui-preview/',
        RedirectView.as_view(pattern_name='admin_panel:dashboard', permanent=False),
    ),
    path(
        'dashboard-preview/',
        RedirectView.as_view(pattern_name='admin_panel:dashboard', permanent=False),
    ),
    path(
        'customers-preview/',
        RedirectView.as_view(pattern_name='admin_panel:customer_list', permanent=False),
    ),
    path(
        'wishlists-preview/',
        RedirectView.as_view(pattern_name='admin_panel:wishlist_list', permanent=False),
    ),
    path(
        'listing-requests-preview/',
        RedirectView.as_view(pattern_name='admin_panel:sell_car_inquiry_list', permanent=False),
    ),
    path(
        'cars-preview/',
        RedirectView.as_view(pattern_name='admin_panel:car_list', permanent=False),
    ),
    path(
        'vehicle-master-preview/',
        RedirectView.as_view(pattern_name='admin_panel:vehicle_master', permanent=False),
    ),
    path(
        'cars-add-preview/',
        RedirectView.as_view(pattern_name='admin_panel:car_add', permanent=False),
    ),
    path(
        'cars/<int:pk>/edit-preview/',
        RedirectView.as_view(pattern_name='admin_panel:car_edit', permanent=False),
    ),
    path(
        'inquiries-preview/',
        RedirectView.as_view(pattern_name='admin_panel:inquiry_list', permanent=False),
    ),
    path(
        'inquiries-preview/<int:pk>/',
        RedirectView.as_view(pattern_name='admin_panel:inquiry_detail', permanent=False),
    ),
    path(
        'csv/import-preview/',
        RedirectView.as_view(pattern_name='admin_panel:csv_import', permanent=False),
    ),
    path(
        'csv/preview-preview/',
        RedirectView.as_view(pattern_name='admin_panel:csv_preview', permanent=False),
    ),
]
