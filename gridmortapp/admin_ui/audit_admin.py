# gridmortapp/admin_ui/audit_admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html, mark_safe
from django.db.models import Q

from unfold.admin import ModelAdmin
from unfold.decorators import display

from gridmortapp.system_models.audit_models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ['user', 'action_display', 'ticket', 'target_user', 'created_at']
    list_filter = ['action', 'created_at', 'user']
    search_fields = ['user__username', 'action', 'ticket__ticket_id', 'target_user__username']
    readonly_fields = ['user', 'action', 'ticket', 'target_user', 'ip_address', 'user_agent', 'details', 'created_at']
    
    list_display_links = ['action_display']
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('user', 'action', 'ticket', 'target_user')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent', 'details')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        is_authorized = (
            request.user.is_superuser or 
            request.user.groups.filter(name__in=['IT Staff', 'Manager', 'Admin']).exists()
        )
        
        if not is_authorized:
            # Regular users see only their own audit logs
            return qs.filter(user=request.user)
        
        return qs
    
    @display(description="Action")
    def action_display(self, obj):
        """Display action with color coding"""
        colors = {
            'USER_LOGIN': '#10B981',
            'USER_LOGOUT': '#6B7280',
            'USER_CREATED': '#3B82F6',
            'USER_UPDATED': '#3B82F6',
            'USER_DELETED': '#EF4444',
            'USER_ROLE_CHANGED': '#8B5CF6',
            'USER_PASSWORD_CHANGED': '#8B5CF6',
            'TICKET_CREATED': '#3B82F6',
            'TICKET_UPDATED': '#F59E0B',
            'TICKET_DELETED': '#EF4444',
            'TICKET_ASSIGNED': '#8B5CF6',
            'TICKET_ESCALATED': '#EC4899',
            'TICKET_REOPENED': '#F59E0B',
            'TICKET_RESOLVED': '#10B981',
            'TICKET_CLOSED': '#6B7280',
            'SLA_BREACHED': '#EF4444',
            'SLA_MARKED_BREACHED': '#EF4444',
            'TICKET_REMINDER_SENT': '#F59E0B',
            'TICKET_AUTO_ESCALATED': '#EF4444',
            'FIRST_RESPONSE': '#10B981',
            'MESSAGE_ADDED': '#14B8A6',
            'MESSAGE_EDITED': '#14B8A6',
            'MESSAGE_DELETED': '#EF4444',
            'REPORT_GENERATED': '#6366F1',
            'REPORT_DOWNLOADED': '#6366F1',
            'REPORT_DELETED': '#EF4444',
            'INVENTORY_ASSIGNED': '#3B82F6',
            'INVENTORY_RETURNED': '#F59E0B',
            'INVENTORY_ADDED': '#10B981',
            'INVENTORY_UPDATED': '#F59E0B',
            'INVENTORY_DELETED': '#EF4444',
            'INVENTORY_MOVEMENT': '#8B5CF6',
            'SYSTEM_ERROR': '#EF4444',
            'SYSTEM_WARNING': '#F59E0B',
            'SYSTEM_CONFIG_CHANGED': '#8B5CF6',
        }
        color = colors.get(obj.action, '#808080')
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{obj.get_action_display()}</span>')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False