# gridmortapp/system_models/audit_models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .ticket_models import Ticket


class AuditLog(models.Model):
    """Global audit log for all system events"""
    
    ACTION_CHOICES = (
        # User actions
        ('USER_LOGIN', 'User Login'),
        ('USER_LOGOUT', 'User Logout'),
        ('USER_CREATED', 'User Created'),
        ('USER_UPDATED', 'User Updated'),
        ('USER_DELETED', 'User Deleted'),
        ('USER_ROLE_CHANGED', 'User Role Changed'),
        ('USER_PASSWORD_CHANGED', 'User Password Changed'),
        
        # Ticket actions
        ('TICKET_CREATED', 'Ticket Created'),
        ('TICKET_UPDATED', 'Ticket Updated'),
        ('TICKET_DELETED', 'Ticket Deleted'),
        ('TICKET_ASSIGNED', 'Ticket Assigned'),
        ('TICKET_ESCALATED', 'Ticket Escalated'),
        ('TICKET_REOPENED', 'Ticket Reopened'),
        ('TICKET_RESOLVED', 'Ticket Resolved'),
        ('TICKET_CLOSED', 'Ticket Closed'),
        ('SLA_BREACHED', 'SLA Breached'),
        ('SLA_MARKED_BREACHED', 'SLA Marked Breached'),
        
        # Message actions
        ('MESSAGE_ADDED', 'Message Added'),
        ('MESSAGE_EDITED', 'Message Edited'),
        ('MESSAGE_DELETED', 'Message Deleted'),
        
        # Report actions
        ('REPORT_GENERATED', 'Report Generated'),
        ('REPORT_DOWNLOADED', 'Report Downloaded'),
        ('REPORT_DELETED', 'Report Deleted'),
        
        # Inventory actions
        ('INVENTORY_ASSIGNED', 'Inventory Assigned'),
        ('INVENTORY_RETURNED', 'Inventory Returned'),
        ('INVENTORY_ADDED', 'Inventory Added'),
        ('INVENTORY_UPDATED', 'Inventory Updated'),
        ('INVENTORY_DELETED', 'Inventory Deleted'),
        
        # System actions
        ('SYSTEM_ERROR', 'System Error'),
        ('SYSTEM_WARNING', 'System Warning'),
        ('SYSTEM_CONFIG_CHANGED', 'System Configuration Changed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ticket = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name='global_audit_logs')
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='target_audit_logs')
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['ticket', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} at {self.created_at}"