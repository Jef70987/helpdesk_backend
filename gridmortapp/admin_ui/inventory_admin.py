# gridmortapp/admin_ui/inventory_admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.html import mark_safe
from django.utils import timezone
from django.contrib import messages
from django import forms

from unfold.admin import ModelAdmin
from unfold.decorators import display

from gridmortapp.models import HardwareCategory, HardwareItem, InventoryMovement
from gridmortapp.system_models.audit_models import AuditLog
from gridmortapp.system_models.ticket_models import Ticket


class HardwareItemForm(forms.ModelForm):
    class Meta:
        model = HardwareItem
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'assigned_to' in self.fields:
            self.fields['assigned_to'].queryset = User.objects.filter(
                Q(groups__name='IT Staff') | 
                Q(groups__name='Manager') | 
                Q(groups__name='Admin') |
                Q(is_superuser=True)
            ).distinct()


@admin.register(HardwareCategory)
class HardwareCategoryAdmin(ModelAdmin):
    list_display = ['name', 'description', 'item_count', 'created_at']
    search_fields = ['name']
    ordering = ['name']
    
    def item_count(self, obj):
        return obj.hardwareitem_set.count()
    item_count.short_description = "Items"


@admin.register(HardwareItem)
class HardwareItemAdmin(ModelAdmin):
    form = HardwareItemForm
    
    list_display = [
        'name', 
        'serial_number', 
        'brand', 
        'model', 
        'status_display', 
        'condition_display', 
        'assigned_to',
        'warranty_display',
        'created_at'
    ]
    
    list_filter = ['status', 'condition', 'category', 'brand']
    search_fields = ['name', 'serial_number', 'brand', 'model', 'assigned_to__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'serial_number', 'brand', 'model', 'category')
        }),
        ('Status & Condition', {
            'fields': ('status', 'condition', 'assigned_to', 'assigned_date')
        }),
        ('Purchase Details', {
            'fields': ('purchase_date', 'purchase_price', 'warranty_expiry', 'supplier', 'invoice_number')
        }),
        ('Additional Information', {
            'fields': ('location', 'notes', 'specification')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        is_authorized = (
            request.user.is_superuser or 
            request.user.groups.filter(name__in=['IT Staff', 'Manager', 'Admin']).exists()
        )
        
        if not is_authorized:
            return qs.filter(assigned_to=request.user)
        
        return qs
    
    def save_model(self, request, obj, form, change):
        old_obj = None
        if change:
            old_obj = HardwareItem.objects.get(pk=obj.pk)
        
        super().save_model(request, obj, form, change)
        
        if not change:
            AuditLog.objects.create(
                user=request.user,
                action='INVENTORY_ADDED',
                details={
                    'item_name': obj.name,
                    'serial_number': obj.serial_number,
                    'brand': obj.brand,
                    'model': obj.model,
                    'created_by': request.user.username
                }
            )
            messages.success(request, f"Hardware item {obj.name} added successfully.")
        
        elif old_obj:
            changes = []
            if old_obj.status != obj.status:
                changes.append(f"Status: {old_obj.get_status_display()} -> {obj.get_status_display()}")
            if old_obj.assigned_to != obj.assigned_to:
                old_assignee = old_obj.assigned_to.username if old_obj.assigned_to else 'Unassigned'
                new_assignee = obj.assigned_to.username if obj.assigned_to else 'Unassigned'
                changes.append(f"Assignee: {old_assignee} -> {new_assignee}")
            if old_obj.condition != obj.condition:
                changes.append(f"Condition: {old_obj.get_condition_display()} -> {obj.get_condition_display()}")
            
            if changes:
                AuditLog.objects.create(
                    user=request.user,
                    action='INVENTORY_UPDATED',
                    details={
                        'item_name': obj.name,
                        'serial_number': obj.serial_number,
                        'changes': ', '.join(changes),
                        'updated_by': request.user.username
                    }
                )
                messages.success(request, f"Hardware item {obj.name} updated successfully.")
    
    def delete_model(self, request, obj):
        AuditLog.objects.create(
            user=request.user,
            action='INVENTORY_DELETED',
            details={
                'item_name': obj.name,
                'serial_number': obj.serial_number,
                'deleted_by': request.user.username
            }
        )
        super().delete_model(request, obj)
        messages.success(request, f"Hardware item {obj.name} deleted successfully.")
    
    @display(description="Status")
    def status_display(self, obj):
        colors = {
            'available': '#10B981',
            'assigned': '#3B82F6',
            'maintenance': '#F59E0B',
            'repair': '#EF4444',
            'retired': '#6B7280',
            'lost': '#EF4444',
        }
        color = colors.get(obj.status, '#808080')
        status_text = obj.get_status_display()
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{status_text}</span>')
    
    @display(description="Condition")
    def condition_display(self, obj):
        colors = {
            'new': '#10B981',
            'good': '#3B82F6',
            'fair': '#F59E0B',
            'poor': '#EF4444',
            'repair_needed': '#EF4444',
        }
        color = colors.get(obj.condition, '#808080')
        condition_text = obj.get_condition_display()
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{condition_text}</span>')
    
    @display(description="Warranty")
    def warranty_display(self, obj):
        if not obj.warranty_expiry:
            return mark_safe('<span style="color: #6B7280; font-weight: bold;">No Warranty</span>')
        
        today = timezone.now().date()
        days_left = (obj.warranty_expiry - today).days
        
        if days_left < 0:
            return mark_safe('<span style="color: #EF4444; font-weight: bold;">Expired</span>')
        elif days_left < 30:
            return mark_safe(f'<span style="color: #F59E0B; font-weight: bold;">{days_left} days left</span>')
        else:
            return mark_safe(f'<span style="color: #10B981; font-weight: bold;">{days_left} days left</span>')
    
    actions = ['mark_available', 'mark_maintenance', 'mark_retired']
    
    def mark_available(self, request, queryset):
        count = queryset.update(status='available', assigned_to=None, assigned_date=None)
        for item in queryset:
            AuditLog.objects.create(
                user=request.user,
                action='INVENTORY_UPDATED',
                details={
                    'item_name': item.name,
                    'serial_number': item.serial_number,
                    'action': 'marked_available'
                }
            )
        self.message_user(request, f"{count} items marked as Available.")
    mark_available.short_description = "Mark selected items as Available"
    
    def mark_maintenance(self, request, queryset):
        count = queryset.update(status='maintenance')
        for item in queryset:
            AuditLog.objects.create(
                user=request.user,
                action='INVENTORY_UPDATED',
                details={
                    'item_name': item.name,
                    'serial_number': item.serial_number,
                    'action': 'marked_maintenance'
                }
            )
        self.message_user(request, f"{count} items marked as Under Maintenance.")
    mark_maintenance.short_description = "Mark selected items as Under Maintenance"
    
    def mark_retired(self, request, queryset):
        count = queryset.update(status='retired', assigned_to=None)
        for item in queryset:
            AuditLog.objects.create(
                user=request.user,
                action='INVENTORY_UPDATED',
                details={
                    'item_name': item.name,
                    'serial_number': item.serial_number,
                    'action': 'marked_retired'
                }
            )
        self.message_user(request, f"{count} items marked as Retired.")
    mark_retired.short_description = "Mark selected items as Retired"


@admin.register(InventoryMovement)
class InventoryMovementAdmin(ModelAdmin):
    list_display = ['hardware', 'movement_type', 'from_user', 'to_user', 'movement_date', 'performed_by']
    list_filter = ['movement_type', 'movement_date']
    search_fields = ['hardware__name', 'hardware__serial_number']
    readonly_fields = ['movement_date']
    
    fieldsets = (
        ('Hardware Information', {
            'fields': ('hardware', 'movement_type')
        }),
        ('User Information', {
            'fields': ('from_user', 'to_user', 'performed_by')
        }),
        ('Additional Information', {
            'fields': ('notes', 'ticket_reference', 'movement_date')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        is_authorized = (
            request.user.is_superuser or 
            request.user.groups.filter(name__in=['IT Staff', 'Manager', 'Admin']).exists()
        )
        
        if not is_authorized:
            return qs.none()
        
        return qs
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.performed_by = request.user
        
        super().save_model(request, obj, form, change)
        
        if obj.movement_type == 'assigned' and obj.to_user:
            obj.hardware.status = 'assigned'
            obj.hardware.assigned_to = obj.to_user
            obj.hardware.assigned_date = timezone.now().date()
            obj.hardware.save()
            
            AuditLog.objects.create(
                user=request.user,
                action='INVENTORY_ASSIGNED',
                details={
                    'hardware': obj.hardware.name,
                    'serial_number': obj.hardware.serial_number,
                    'assigned_to': obj.to_user.username,
                    'performed_by': request.user.username
                }
            )
            messages.success(request, f"Hardware {obj.hardware.name} assigned to {obj.to_user.username}")
        
        elif obj.movement_type == 'returned':
            obj.hardware.status = 'available'
            obj.hardware.assigned_to = None
            obj.hardware.assigned_date = None
            obj.hardware.save()
            
            AuditLog.objects.create(
                user=request.user,
                action='INVENTORY_RETURNED',
                details={
                    'hardware': obj.hardware.name,
                    'serial_number': obj.hardware.serial_number,
                    'returned_by': request.user.username
                }
            )
            messages.success(request, f"Hardware {obj.hardware.name} returned to inventory")
        
        elif obj.movement_type == 'maintenance':
            obj.hardware.status = 'maintenance'
            obj.hardware.save()
            messages.success(request, f"Hardware {obj.hardware.name} sent for maintenance")
        
        elif obj.movement_type == 'retired':
            obj.hardware.status = 'retired'
            obj.hardware.assigned_to = None
            obj.hardware.save()
            messages.success(request, f"Hardware {obj.hardware.name} retired from service")
        
        AuditLog.objects.create(
            user=request.user,
            action='INVENTORY_MOVEMENT',
            details={
                'hardware': obj.hardware.name,
                'movement_type': obj.get_movement_type_display(),
                'performed_by': request.user.username
            }
        )