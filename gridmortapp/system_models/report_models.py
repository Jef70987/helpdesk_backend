from django.db import models
from django.contrib.auth.models import User
from .ticket_models import Ticket
from .inventory_models import HardwareItem


class ReportType(models.Model):
    """Types of reports available"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    report_code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Report(models.Model):
    """Generated reports"""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('scheduled', 'Scheduled'),
        ('archived', 'Archived'),
    )
    
    FORMAT_CHOICES = (
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('html', 'HTML'),
    )
    
    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Report parameters
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    filters = models.JSONField(default=dict, blank=True)  # Store filter criteria
    
    # Report details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='pdf')
    
    # File storage
    file_path = models.CharField(max_length=500, blank=True, null=True)
    file_size = models.IntegerField(null=True, blank=True)  # Size in bytes
    
    # Statistics for tickets
    total_tickets = models.IntegerField(default=0)
    resolved_tickets = models.IntegerField(default=0)
    unresolved_tickets = models.IntegerField(default=0)
    avg_resolution_time = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Statistics for inventory
    total_hardware = models.IntegerField(default=0)
    assigned_hardware = models.IntegerField(default=0)
    available_hardware = models.IntegerField(default=0)
    maintenance_hardware = models.IntegerField(default=0)
    
    # Generation
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_reports')
    generated_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    is_scheduled = models.BooleanField(default=False)
    recurrence = models.CharField(max_length=50, blank=True, null=True)  # e.g., daily, weekly, monthly
    
    # Additional data
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.title} - {self.generated_at}"


class ReportLog(models.Model):
    """Log of report generation activities"""
    ACTION_CHOICES = (
        ('generated', 'Generated'),
        ('downloaded', 'Downloaded'),
        ('emailed', 'Emailed'),
        ('scheduled', 'Scheduled'),
        ('deleted', 'Deleted'),
        ('viewed', 'Viewed'),
    )
    
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.report.title} - {self.action} - {self.timestamp}"