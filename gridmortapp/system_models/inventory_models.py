from django.db import models
from django.contrib.auth.models import User
from .ticket_models import Ticket


class HardwareCategory(models.Model):
    """Categories of hardware (e.g., Laptops, Desktops, Printers)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Hardware Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class HardwareItem(models.Model):
    """Individual hardware items in inventory"""
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('maintenance', 'Under Maintenance'),
        ('repair', 'Being Repaired'),
        ('retired', 'Retired'),
        ('lost', 'Lost'),
    )
    
    CONDITION_CHOICES = (
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('repair_needed', 'Repair Needed'),
    )
    
    # Basic information
    name = models.CharField(max_length=200)
    serial_number = models.CharField(max_length=100, unique=True)
    model = models.CharField(max_length=100)
    brand = models.CharField(max_length=100)
    category = models.ForeignKey(HardwareCategory, on_delete=models.SET_NULL, null=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_hardware')
    assigned_date = models.DateField(null=True, blank=True)
    
    # Purchase details
    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=200, blank=True, null=True)
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Additional information
    location = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    specification = models.JSONField(default=dict, blank=True)  # Flexible spec storage
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.brand} {self.model} - {self.serial_number}"


class InventoryMovement(models.Model):
    """Track hardware movements (assignments, returns, transfers)"""
    MOVEMENT_TYPES = (
        ('assigned', 'Assigned to User'),
        ('returned', 'Returned from User'),
        ('transferred', 'Transferred to Another User'),
        ('maintenance', 'Sent for Maintenance'),
        ('repair', 'Sent for Repair'),
        ('retired', 'Retired from Service'),
    )
    
    hardware = models.ForeignKey(HardwareItem, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    
    # Users involved
    from_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hardware_out')
    to_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hardware_in')
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='hardware_movements')
    
    # Details
    movement_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    ticket_reference = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-movement_date']
    
    def __str__(self):
        return f"{self.hardware} - {self.movement_type} - {self.movement_date}"