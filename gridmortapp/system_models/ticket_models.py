# gridmortapp/system_models/ticket_models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid


class TicketCategory(models.Model):
    """Categories with sub-categories support"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    routing_group = models.CharField(max_length=50, blank=True, null=True, help_text="Team/group to route tickets to")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Ticket Categories"
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name


class TicketPriority(models.Model):
    """Priority levels with SLA targets"""
    name = models.CharField(max_length=50, unique=True)
    level = models.IntegerField(unique=True, help_text="1=Lowest, 5=Critical")
    color_code = models.CharField(max_length=7, default='#808080')
    
    response_time_minutes = models.IntegerField(default=240, help_text="SLA response time in minutes")
    resolution_time_minutes = models.IntegerField(default=2880, help_text="SLA resolution time in minutes")
    escalation_time_minutes = models.IntegerField(null=True, blank=True, help_text="Time in minutes before auto-escalation")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Ticket Priorities"
        ordering = ['level']
    
    def __str__(self):
        return f"{self.name} (SLA: {self.response_time_minutes//60}h response)"


class TicketStatus(models.Model):
    """Lifecycle status with transition rules"""
    STATUS_TYPES = (
        ('new', 'New'),
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending_customer', 'Pending Customer'),
        ('pending_third_party', 'Pending Third Party'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('canceled', 'Canceled'),
    )
    
    name = models.CharField(max_length=50, unique=True)
    status_type = models.CharField(max_length=20, choices=STATUS_TYPES, unique=True)
    is_active = models.BooleanField(default=True)
    is_terminal = models.BooleanField(default=False)
    color_code = models.CharField(max_length=7, default='#808080')
    display_order = models.IntegerField(default=0)
    allowed_next_statuses = models.JSONField(default=list, blank=True, help_text="List of allowed next status types")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Ticket Statuses"
        ordering = ['display_order']
    
    def __str__(self):
        return self.name


class Ticket(models.Model):
    """Main ticket model with professional features"""
    
    TICKET_TYPES = (
        ('question', 'Question'),
        ('incident', 'Incident/Bug'),
        ('feature_request', 'Feature Request'),
        ('task', 'Task'),
        ('problem', 'Problem'),
    )
    
    SOURCES = (
        ('email', 'Email'),
        ('portal', 'Portal'),
        ('phone', 'Phone'),
        ('chat', 'Chat'),
        ('api', 'API'),
    )
    
    IMPACT_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    # 1. Identity & Routing Elements
    ticket_id = models.CharField(max_length=30, unique=True, blank=True)
    external_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    # 2. Requestor & Assignee
    requestor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='requested_tickets',
        verbose_name="Requestor"
    )
    assignee = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_tickets',
        verbose_name="Assignee"
    )
    
    # 3. Categorization
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPES, default='incident')
    category = models.ForeignKey(TicketCategory, on_delete=models.SET_NULL, null=True, related_name='tickets')
    priority = models.ForeignKey(TicketPriority, on_delete=models.SET_NULL, null=True, related_name='tickets')
    status = models.ForeignKey(TicketStatus, on_delete=models.SET_NULL, null=True, related_name='tickets')
    
    # 4. Core Content
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # 5. Chronological Metadata (Auto-tracked - READONLY in admin)
    created_at = models.DateTimeField(auto_now_add=True)
    first_assignment_at = models.DateTimeField(null=True, blank=True, editable=False)
    first_response_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_modified_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True, editable=False)
    closed_at = models.DateTimeField(null=True, blank=True, editable=False)
    
    # 6. SLA Tracking
    sla_response_deadline = models.DateTimeField(null=True, blank=True)
    sla_resolution_deadline = models.DateTimeField(null=True, blank=True)
    sla_breached = models.BooleanField(default=False)
    sla_breach_reason = models.TextField(blank=True, null=True)
    
    # 7. Lifecycle Control
    reopen_count = models.IntegerField(default=0)
    is_reopened = models.BooleanField(default=False)
    escalation_level = models.IntegerField(default=0)
    escalated_at = models.DateTimeField(null=True, blank=True)
    
    # 8. Time Tracking
    time_spent_minutes = models.IntegerField(default=0)
    
    # 9. Additional Context
    source = models.CharField(max_length=20, choices=SOURCES, default='portal')
    urgency = models.BooleanField(default=False, help_text="Check if this is urgent")
    impact = models.CharField(max_length=20, choices=IMPACT_LEVELS, default='medium')
    tags = models.JSONField(default=list, blank=True)
    
    # 10. Notification Tracking (NEW)
    last_notification_at = models.DateTimeField(null=True, blank=True, help_text="Last time a notification was sent")
    notification_count = models.IntegerField(default=0, help_text="Number of notifications sent")
    response_reminder_count = models.IntegerField(default=0, help_text="Number of response reminders sent")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_id']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['last_notification_at']),
        ]
    
    def __str__(self):
        return f"{self.ticket_id} - {self.title[:50]}"
    
    def save(self, *args, **kwargs):
        # Generate ticket ID if not exists
        if not self.ticket_id:
            year = timezone.now().strftime('%Y')
            month = timezone.now().strftime('%m')
            prefix = 'TKT'
            
            last_ticket = Ticket.objects.filter(
                ticket_id__startswith=f'{prefix}-{year}{month}'
            ).order_by('ticket_id').last()
            
            if last_ticket:
                last_num = int(last_ticket.ticket_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.ticket_id = f'{prefix}-{year}{month}-{new_num:05d}'
        
        # Track first assignment
        if self.assignee and not self.first_assignment_at:
            self.first_assignment_at = timezone.now()
        
        # Track resolution
        if self.status and self.status.status_type in ['resolved', 'closed'] and not self.resolved_at:
            self.resolved_at = timezone.now()
        
        # Track closure
        if self.status and self.status.status_type == 'closed' and not self.closed_at:
            self.closed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def calculate_sla_status(self):
        """Calculate SLA status"""
        if not self.priority:
            return None
        
        now = timezone.now()
        
        # Response SLA
        if self.first_response_at:
            response_time = (self.first_response_at - self.created_at).total_seconds() / 60
        else:
            response_time = (now - self.created_at).total_seconds() / 60
        
        response_deadline = self.priority.response_time_minutes
        response_breached = response_time > response_deadline
        
        # Resolution SLA
        if self.resolved_at:
            resolution_time = (self.resolved_at - self.created_at).total_seconds() / 60
        else:
            resolution_time = (now - self.created_at).total_seconds() / 60
        
        resolution_deadline = self.priority.resolution_time_minutes
        resolution_breached = resolution_time > resolution_deadline
        
        return {
            'response': {
                'elapsed': response_time,
                'deadline': response_deadline,
                'breached': response_breached,
            },
            'resolution': {
                'elapsed': resolution_time,
                'deadline': resolution_deadline,
                'breached': resolution_breached,
            }
        }


class TicketMessage(models.Model):
    """Communication thread model"""
    MESSAGE_TYPES = (
        ('public', 'Public Message'),
        ('internal', 'Internal Note'),
        ('system', 'System Notification'),
    )
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ticket_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='public')
    
    content = models.TextField()
    html_content = models.TextField(blank=True, null=True)
    attachments = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    edit_history = models.JSONField(default=list, blank=True)
    
    mentions = models.ManyToManyField(User, related_name='mentioned_in_messages', blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.ticket.ticket_id} - {self.message_type} by {self.author.username if self.author else 'System'}"