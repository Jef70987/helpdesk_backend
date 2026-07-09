from django.urls import path
from gridmortapp.views.admin_views import (
    AdminDashboardView,
    AdminTicketListView,
    AdminTicketDetailView,
    AdminTicketMessageView,
    AdminUserListView,
    AdminUserDetailView,
    AdminHardwareCategoriesView,
    AdminHardwareListView,
    AdminHardwareCreateView,
    AdminHardwareDetailView,
    AdminHardwareMovementsView,
    AdminHardwareReportView,
    AdminHardwareExportView,
    AdminReportSummaryView,
    AdminReportGenerateView,
    AdminReportExportView,
    AdminAuditLogView,
)

urlpatterns = [
    # Dashboard
    path('dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Tickets
    path('tickets/', AdminTicketListView.as_view(), name='admin_tickets'),
    path('tickets/<int:pk>/', AdminTicketDetailView.as_view(), name='admin_ticket_detail'),
    path('tickets/<int:pk>/messages/', AdminTicketMessageView.as_view(), name='admin_ticket_messages'),
    
    # Users
    path('users/', AdminUserListView.as_view(), name='admin_users'),
    path('users/<int:pk>/', AdminUserDetailView.as_view(), name='admin_user_detail'),
    
    # Hardware
    path('hardware/categories/', AdminHardwareCategoriesView.as_view(), name='admin_hardware_categories'),
    path('hardware/', AdminHardwareListView.as_view(), name='admin_hardware'),
    path('hardware/create/', AdminHardwareCreateView.as_view(), name='admin_hardware_create'),
    path('hardware/<int:pk>/', AdminHardwareDetailView.as_view(), name='admin_hardware_detail'),
    path('hardware/movements/', AdminHardwareMovementsView.as_view(), name='admin_hardware_movements'),
    path('hardware/report/', AdminHardwareReportView.as_view(), name='admin_hardware_report'),
    path('hardware/export/', AdminHardwareExportView.as_view(), name='admin_hardware_export'),
    
    # Reports
    path('reports/summary/', AdminReportSummaryView.as_view(), name='admin_reports_summary'),
    path('reports/generate/', AdminReportGenerateView.as_view(), name='admin_reports_generate'),
    path('reports/export/', AdminReportExportView.as_view(), name='admin_reports_export'),
    
    # Audit Logs
    path('audit-logs/', AdminAuditLogView.as_view(), name='admin_audit_logs'),
]