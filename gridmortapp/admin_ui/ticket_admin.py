# gridmortapp/admin_ui/ticket_admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from django.utils.html import mark_safe
from django import forms
from django.shortcuts import redirect
from django.contrib import messages

from unfold.admin import ModelAdmin
from unfold.decorators import display

from gridmortapp.system_models.ticket_models import (
    TicketCategory, TicketPriority, TicketStatus, 
    Ticket, TicketMessage
)
from gridmortapp.system_models.audit_models import AuditLog


class TicketAdminForm(forms.ModelForm):
    """Custom form with filtered dropdowns and auto-fill"""
    
    class Meta:
        model = Ticket
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if hasattr(self, '_request'):
            request = self._request
        else:
            request = None
        
        # Filter assignee to only show Support Agents and IT Staff
        if 'assignee' in self.fields:
            self.fields['assignee'].queryset = User.objects.filter(
                Q(groups__name='Support Agents') | 
                Q(groups__name='IT Staff') | 
                Q(groups__name='Manager') | 
                Q(groups__name='Admin') |
                Q(is_superuser=True)
            ).distinct()
        
        # Check if user is authorized
        is_authorized = False
        if request:
            is_authorized = (
                request.user.is_superuser or 
                request.user.groups.filter(
                    name__in=['IT Staff', 'Support Agents', 'Manager', 'Admin']
                ).exists()
            )
        
        # Hide requestor field for regular users
        if 'requestor' in self.fields and not is_authorized:
            self.fields['requestor'].widget = forms.HiddenInput()
            self.fields['requestor'].required = False
        
        # Hide external_id for regular users
        if 'external_id' in self.fields and not is_authorized:
            self.fields['external_id'].widget = forms.HiddenInput()
            self.fields['external_id'].required = False
        
        # For regular users, hide and disable assignee, priority, status
        if not is_authorized:
            for field_name in ['assignee', 'priority', 'status']:
                if field_name in self.fields:
                    self.fields[field_name].widget = forms.HiddenInput()
                    self.fields[field_name].required = False
        
        # Filter status based on current status transitions (only for authorized users)
        if is_authorized and self.instance and self.instance.pk and self.instance.status:
            current_status = self.instance.status
            if current_status.allowed_next_statuses:
                self.fields['status'].queryset = TicketStatus.objects.filter(
                    status_type__in=current_status.allowed_next_statuses
                )
        
        # Auto-set default priority based on category for new tickets
        if not self.instance.pk and self.instance.category:
            if self.instance.category.name in ['Hardware', 'Network']:
                try:
                    default_priority = TicketPriority.objects.get(level=3)
                    self.initial['priority'] = default_priority
                except TicketPriority.DoesNotExist:
                    pass
    
    def clean_requestor(self):
        """Auto-set requestor to current user"""
        if not self.cleaned_data.get('requestor'):
            if hasattr(self, '_request') and self._request:
                return self._request.user
        return self.cleaned_data.get('requestor')


@admin.register(TicketCategory)
class TicketCategoryAdmin(ModelAdmin):
    list_display = ['name', 'parent', 'routing_group', 'ticket_count', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'routing_group']
    ordering = ['name']
    
    def ticket_count(self, obj):
        return obj.tickets.count()
    ticket_count.short_description = "Tickets"


@admin.register(TicketPriority)
class TicketPriorityAdmin(ModelAdmin):
    list_display = ['name', 'level', 'color_code', 'response_time_minutes', 'resolution_time_minutes', 'is_active']
    list_editable = ['level', 'color_code', 'response_time_minutes', 'resolution_time_minutes', 'is_active']
    ordering = ['level']
    
    fieldsets = (
        ('Priority Information', {
            'fields': ('name', 'level', 'color_code')
        }),
        ('SLA Targets', {
            'fields': ('response_time_minutes', 'resolution_time_minutes', 'escalation_time_minutes')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(TicketStatus)
class TicketStatusAdmin(ModelAdmin):
    list_display = ['name', 'status_type', 'is_active', 'is_terminal', 'color_code']
    list_editable = ['is_active', 'is_terminal', 'color_code']
    ordering = ['display_order']


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    form = TicketAdminForm
    
    list_display = [
        'ticket_id',
        'title_preview', 
        'status_colored', 
        'priority_colored', 
        'category', 
        'requestor', 
        'assignee', 
        'created_at',
        'sla_indicator',
        'age_display',
        'notification_status'
    ]
    
    list_filter = [
        'status', 
        'priority', 
        'category', 
        'ticket_type',
        'source', 
        'created_at',
        'assignee',
        'sla_breached',
        'is_reopened'
    ]
    
    search_fields = ['ticket_id', 'title', 'description', 'requestor__username', 'requestor__email']
    
    readonly_fields = [
        'ticket_id',
        'created_at',
        'first_assignment_at',
        'first_response_at',
        'last_modified_at',
        'resolved_at',
        'closed_at',
        'reopen_count',
        'escalation_level',
        'escalated_at',
        'last_notification_at',
        'notification_count',
        'response_reminder_count'
    ]
    
    fieldsets = (
        ('Identity & Routing', {
            'fields': ('ticket_id', 'external_id', 'requestor', 'assignee')
        }),
        ('Categorization & Priority', {
            'fields': ('ticket_type', 'category', 'priority', 'status')
        }),
        ('Content', {
            'fields': ('title', 'description')
        }),
        ('SLA Information', {
            'fields': ('sla_response_deadline', 'sla_resolution_deadline', 'sla_breached', 'sla_breach_reason'),
            'classes': ('collapse',)
        }),
        ('Time Tracking', {
            'fields': ('created_at', 'first_assignment_at', 'first_response_at', 'last_modified_at',
                      'resolved_at', 'closed_at', 'time_spent_minutes'),
            'classes': ('collapse',)
        }),
        ('Lifecycle Control', {
            'fields': ('reopen_count', 'is_reopened', 'escalation_level', 'escalated_at'),
            'classes': ('collapse',)
        }),
        ('Notification Tracking', {
            'fields': ('last_notification_at', 'notification_count', 'response_reminder_count'),
            'classes': ('collapse',)
        }),
        ('Advanced', {
            'fields': ('source', 'urgency', 'impact', 'tags'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Pass request to form for permission checking"""
        form = super().get_form(request, obj, **kwargs)
        form._request = request
        
        is_authorized = (
            request.user.is_superuser or 
            request.user.groups.filter(
                name__in=['IT Staff', 'Support Agents', 'Manager', 'Admin']
            ).exists()
        )
        
        if not is_authorized:
            restricted_fields = [
                'assignee', 'priority', 'status', 'sla_response_deadline', 
                'sla_resolution_deadline', 'sla_breached', 'sla_breach_reason',
                'source', 'impact', 'escalation_level', 'escalated_at',
                'last_notification_at', 'notification_count', 'response_reminder_count'
            ]
            
            for field in restricted_fields:
                if field in form.base_fields:
                    form.base_fields[field].widget = forms.HiddenInput()
                    form.base_fields[field].required = False
        
        return form
    
    def get_queryset(self, request):
        """Filter tickets based on user role"""
        qs = super().get_queryset(request)
        
        is_authorized = (
            request.user.is_superuser or 
            request.user.groups.filter(
                name__in=['IT Staff', 'Support Agents', 'Manager', 'Admin']
            ).exists()
        )
        
        if not is_authorized:
            return qs.filter(requestor=request.user)
        
        return qs
    
    def get_readonly_fields(self, request, obj=None):
        """Make additional fields readonly based on user role"""
        readonly = list(self.readonly_fields)
        
        is_authorized = (
            request.user.is_superuser or 
            request.user.groups.filter(
                name__in=['IT Staff', 'Support Agents', 'Manager', 'Admin']
            ).exists()
        )
        
        if not is_authorized:
            restricted_readonly = ['assignee', 'priority', 'status']
            for field in restricted_readonly:
                if field not in readonly:
                    readonly.append(field)
        
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Save with automation tracking"""
        old_obj = None
        if change:
            old_obj = Ticket.objects.get(pk=obj.pk)
        
        if not change:
            obj.requestor = request.user
        
        if not obj.status:
            try:
                obj.status = TicketStatus.objects.get(status_type='new')
            except TicketStatus.DoesNotExist:
                pass
        
        super().save_model(request, obj, form, change)
        
        if not change:
            AuditLog.objects.create(
                ticket=obj,
                user=request.user,
                action='TICKET_CREATED',
                details={
                    'ticket_id': obj.ticket_id,
                    'title': obj.title,
                    'category': obj.category.name if obj.category else None,
                    'created_by': request.user.username
                }
            )
            messages.success(request, f"Ticket {obj.ticket_id} created successfully.")
        else:
            messages.success(request, f"Ticket {obj.ticket_id} updated successfully.")
    
    def delete_model(self, request, obj):
        AuditLog.objects.create(
            ticket=obj,
            user=request.user,
            action='TICKET_DELETED',
            details={
                'ticket_id': obj.ticket_id,
                'title': obj.title,
                'deleted_by': request.user.username
            }
        )
        super().delete_model(request, obj)
        messages.success(request, f"Ticket {obj.ticket_id} deleted successfully.")
    
    @display(description="Title")
    def title_preview(self, obj):
        return obj.title[:60] + '...' if len(obj.title) > 60 else obj.title
    
    @display(description="Status")
    def status_colored(self, obj):
        if obj.status:
            color = obj.status.color_code or '#808080'
            name = obj.status.name or 'None'
            return mark_safe(f'<span style="color: {color}; font-weight: bold;">{name}</span>')
        return 'None'
    
    @display(description="Priority")
    def priority_colored(self, obj):
        if obj.priority:
            color = obj.priority.color_code or '#808080'
            name = obj.priority.name or 'None'
            return mark_safe(f'<span style="color: {color}; font-weight: bold;">{name}</span>')
        return 'None'
    
    @display(description="SLA")
    def sla_indicator(self, obj):
        if obj.resolved_at or obj.closed_at:
            return mark_safe('<span style="color: #10B981; font-weight: bold;">Met</span>')
        
        if obj.sla_breached:
            return mark_safe('<span style="color: #EF4444; font-weight: bold;">Breached</span>')
        
        sla_status = obj.calculate_sla_status()
        if sla_status and sla_status.get('response'):
            response_deadline = sla_status['response'].get('deadline', 0)
            response_elapsed = sla_status['response'].get('elapsed', 0)
            if response_deadline > 0 and (response_elapsed / response_deadline) > 0.8:
                return mark_safe('<span style="color: #F59E0B; font-weight: bold;">At Risk</span>')
        
        return mark_safe('<span style="color: #3B82F6; font-weight: bold;">In SLA</span>')
    
    @display(description="Age")
    def age_display(self, obj):
        now = timezone.now()
        age = now - obj.created_at
        
        if age.days > 0:
            return f"{age.days}d {age.seconds//3600}h"
        elif age.seconds > 3600:
            return f"{age.seconds//3600}h"
        else:
            return f"{age.seconds//60}m"
    
    @display(description="Notifications")
    def notification_status(self, obj):
        if obj.notification_count > 0:
            return mark_safe(f'<span style="color: #F59E0B;">{obj.notification_count} sent</span>')
        return 'None'
    
    actions = ['assign_to_me', 'escalate_ticket', 'mark_sla_breached', 'view_audit_log', 'reset_notifications']
    
    def assign_to_me(self, request, queryset):
        is_authorized = (
            request.user.is_superuser or 
            request.user.groups.filter(
                name__in=['IT Staff', 'Support Agents', 'Manager', 'Admin']
            ).exists()
        )
        
        if not is_authorized:
            self.message_user(request, "You don't have permission to assign tickets.", level='ERROR')
            return
        
        updated = queryset.filter(assignee__isnull=True).update(assignee=request.user)
        
        for ticket in queryset.filter(assignee__isnull=True):
            AuditLog.objects.create(
                ticket=ticket,
                user=request.user,
                action='TICKET_ASSIGNED',
                details={
                    'ticket_id': ticket.ticket_id,
                    'assignee': request.user.username,
                    'action': 'bulk_assign'
                }
            )
        
        self.message_user(request, f"{updated} tickets assigned to you.")
    assign_to_me.short_description = "Assign selected tickets to me"
    
    def escalate_ticket(self, request, queryset):
        is_authorized = (
            request.user.is_superuser or 
            request.user.groups.filter(
                name__in=['IT Staff', 'Support Agents', 'Manager', 'Admin']
            ).exists()
        )
        
        if not is_authorized:
            self.message_user(request, "You don't have permission to escalate tickets.", level='ERROR')
            return
        
        for ticket in queryset:
            ticket.escalation_level += 1
            ticket.escalated_at = timezone.now()
            ticket.save()
            
            AuditLog.objects.create(
                ticket=ticket,
                user=request.user,
                action='TICKET_ESCALATED',
                details={
                    'ticket_id': ticket.ticket_id,
                    'new_level': ticket.escalation_level,
                    'escalated_by': request.user.username
                }
            )
        
        self.message_user(request, f"{queryset.count()} tickets escalated.")
    escalate_ticket.short_description = "Escalate selected tickets"
    
    def mark_sla_breached(self, request, queryset):
        is_authorized = (
            request.user.is_superuser or 
            request.user.groups.filter(
                name__in=['IT Staff', 'Support Agents', 'Manager', 'Admin']
            ).exists()
        )
        
        if not is_authorized:
            self.message_user(request, "You don't have permission to mark SLA breaches.", level='ERROR')
            return
        
        count = queryset.update(sla_breached=True, sla_breach_reason="Manually marked as breached")
        
        for ticket in queryset:
            AuditLog.objects.create(
                ticket=ticket,
                user=request.user,
                action='SLA_MARKED_BREACHED',
                details={
                    'ticket_id': ticket.ticket_id,
                    'marked_by': request.user.username
                }
            )
        
        self.message_user(request, f"{count} tickets marked as SLA breached.")
    mark_sla_breached.short_description = "Mark selected tickets as SLA breached"
    
    def view_audit_log(self, request, queryset):
        if queryset.count() == 1:
            ticket = queryset.first()
            return redirect(
                f"/admin/gridmortapp/auditlog/?ticket__id__exact={ticket.id}"
            )
        else:
            self.message_user(request, "Please select only one ticket to view audit log.", level='WARNING')
    view_audit_log.short_description = "View audit log for selected ticket"
    
    def reset_notifications(self, request, queryset):
        count = queryset.update(notification_count=0, response_reminder_count=0)
        self.message_user(request, f"Notification counters reset for {count} tickets.")
    reset_notifications.short_description = "Reset notification counters"


# ============================================================
# TICKET MESSAGE ADMIN - WITH PROPER FILTERING
# ============================================================
class TicketMessageForm(forms.ModelForm):
    """Custom form for ticket messages with filtered dropdowns"""
    
    class Meta:
        model = TicketMessage
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if hasattr(self, '_request'):
            request = self._request
        else:
            request = None
        
        # Filter ticket dropdown - users can only see their own tickets
        if 'ticket' in self.fields:
            if request and not (
                request.user.is_superuser or 
                request.user.groups.filter(
                    name__in=['IT Staff', 'Support Agents', 'Manager', 'Admin']
                ).exists()
            ):
                # Regular users see only their own tickets
                self.fields['ticket'].queryset = Ticket.objects.filter(requestor=request.user)
        
        # Auto-set author to current user
        if 'author' in self.fields and request:
            self.fields['author'].initial = request.user
            self.fields['author'].widget = forms.HiddenInput()
            self.fields['author'].required = False
        
        # For regular users, restrict message type to only 'public'
        if 'message_type' in self.fields:
            if request and not (
                request.user.is_superuser or 
                request.user.groups.filter(
                    name__in=['IT Staff', 'Support Agents', 'Manager', 'Admin']
                ).exists()
            ):
                self.fields['message_type'].choices = [
                    ('public', 'Public Message')
                ]
    
    def clean_author(self):
        """Auto-set author to current user"""
        if not self.cleaned_data.get('author'):
            if hasattr(self, '_request') and self._request:
                return self._request.user
        return self.cleaned_data.get('author')


@admin.register(TicketMessage)
class TicketMessageAdmin(ModelAdmin):
    form = TicketMessageForm
    
    list_display = ['ticket', 'author', 'message_type_display', 'content_preview', 'created_at']
    list_filter = ['message_type', 'created_at', 'author']
    search_fields = ['content', 'ticket__ticket_id', 'author__username']
    readonly_fields = ['created_at', 'updated_at', 'is_edited']
    
    fieldsets = (
        ('Message Information', {
            'fields': ('ticket', 'author', 'message_type', 'content', 'html_content')
        }),
        ('Attachments & Mentions', {
            'fields': ('attachments', 'mentions')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'is_edited', 'edit_history')
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Pass request to form"""
        form = super().get_form(request, obj, **kwargs)
        form._request = request
        return form
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        is_authorized = (
            request.user.is_superuser or 
            request.user.groups.filter(
                name__in=['IT Staff', 'Support Agents', 'Manager', 'Admin']
            ).exists()
        )
        
        if not is_authorized:
            # Regular users see only messages from their own tickets
            ticket_ids = Ticket.objects.filter(requestor=request.user).values_list('id', flat=True)
            return qs.filter(ticket__id__in=ticket_ids)
        
        return qs
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        
        super().save_model(request, obj, form, change)
        
        AuditLog.objects.create(
            ticket=obj.ticket,
            user=request.user,
            action='MESSAGE_ADDED',
            details={
                'message_id': obj.id,
                'type': obj.message_type,
                'ticket_id': obj.ticket.ticket_id
            }
        )
    
    @display(description="Type")
    def message_type_display(self, obj):
        """Display message type with color coding"""
        colors = {
            'public': '#10B981',
            'internal': '#F59E0B',
            'system': '#6B7280',
        }
        color = colors.get(obj.message_type, '#808080')
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{obj.get_message_type_display()}</span>')
    
    @display(description="Content Preview")
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content