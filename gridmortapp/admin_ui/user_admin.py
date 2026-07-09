# gridmortapp/admin_ui/user_admin.py
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.db.models import Q
from django.utils.html import format_html, mark_safe
from django import forms
from django.contrib import messages

from unfold.admin import ModelAdmin, StackedInline, display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from gridmortapp.models import Department, EmployeeProfile
from gridmortapp.system_models.audit_models import AuditLog


@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ['name', 'code', 'description', 'employee_count', 'created_at']
    search_fields = ['name', 'code']
    ordering = ['name']
    
    def employee_count(self, obj):
        return obj.employeeprofile_set.count()
    employee_count.short_description = "Employees"


class EmployeeProfileInline(StackedInline):
    model = EmployeeProfile
    can_delete = False
    verbose_name_plural = 'Employee Profile'
    fieldsets = (
        ('Personal Information', {
            'fields': ('employee_id', 'department', 'user_type', 'position')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'office_location')
        }),
        ('Employment Details', {
            'fields': ('hire_date',)
        }),
        ('System Information', {
            'fields': ('is_active', 'last_login_ip')
        }),
    )


class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    
    list_display = [
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'user_type_display',
        'department_display',
        'ticket_count_display',
        'is_staff', 
        'is_active',
        'last_login'
    ]
    
    list_filter = [
        'is_staff', 
        'is_active', 
        'profile__department__name',
        'profile__user_type',
        'groups',
        'last_login'
    ]
    
    search_fields = ['username', 'email', 'first_name', 'last_name', 'profile__employee_id']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    filter_horizontal = ('groups', 'user_permissions')
    
    def get_queryset(self, request):
        """Filter users based on role"""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        if request.user.groups.filter(name__in=['Manager', 'IT Staff', 'Admin']).exists():
            return qs.filter(is_superuser=False)
        
        # Regular users see only themselves
        return qs.filter(id=request.user.id)
    
    def get_inlines(self, request, obj=None):
        """Only show employee fields when editing existing users"""
        if obj is None:
            return ()
        return (EmployeeProfileInline,)
    
    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly based on user role"""
        readonly = []
        
        if not request.user.is_superuser:
            if not request.user.groups.filter(name__in=['Manager', 'IT Staff', 'Admin']).exists():
                readonly.extend(['is_staff', 'is_superuser', 'groups', 'user_permissions'])
        
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Save with audit logging"""
        super().save_model(request, obj, form, change)
        
        if not change:
            AuditLog.objects.create(
                user=request.user,
                action='USER_CREATED',
                target_user=obj,
                details={
                    'username': obj.username,
                    'email': obj.email,
                    'created_by': request.user.username
                }
            )
            messages.success(request, f"User {obj.username} created successfully.")
        else:
            AuditLog.objects.create(
                user=request.user,
                action='USER_UPDATED',
                target_user=obj,
                details={
                    'username': obj.username,
                    'email': obj.email,
                    'updated_by': request.user.username
                }
            )
            messages.success(request, f"User {obj.username} updated successfully.")
    
    def delete_model(self, request, obj):
        """Log deletion"""
        AuditLog.objects.create(
            user=request.user,
            action='USER_DELETED',
            target_user=obj,
            details={
                'username': obj.username,
                'email': obj.email,
                'deleted_by': request.user.username
            }
        )
        super().delete_model(request, obj)
        messages.success(request, f"User {obj.username} deleted successfully.")
    
    @display(description="User Type", ordering='profile__user_type')
    def user_type_display(self, obj):
        """Display user type with color coding"""
        try:
            user_type = obj.profile.user_type
            colors = {
                'admin': '#EF4444',
                'manager': '#F59E0B',
                'it_staff': '#3B82F6',
                'employee': '#10B981',
            }
            color = colors.get(user_type, '#808080')
            return mark_safe(
                f'<span style="color: {color}; font-weight: bold;">{user_type.replace("_", " ").title() if user_type else "Employee"}</span>'
            )
        except:
            return 'Employee'
    
    @display(description="Department", ordering='profile__department__name')
    def department_display(self, obj):
        """Display department name"""
        try:
            return obj.profile.department.name if obj.profile.department else 'Not Assigned'
        except:
            return 'Not Assigned'
    
    @display(description="Tickets", ordering='ticket_count')
    def ticket_count_display(self, obj):
        """Display ticket count with link to user's tickets"""
        try:
            from gridmortapp.system_models.ticket_models import Ticket
            count = Ticket.objects.filter(requestor=obj).count()
            
            if count > 0:
                return mark_safe(
                    f'<a href="/admin/gridmortapp/ticket/?requestor__id__exact={obj.id}" style="color: #3B82F6; font-weight: bold;">{count}</a>'
                )
            return '0'
        except:
            return '0'
    
    actions = ['make_it_staff', 'make_manager', 'make_employee', 'activate_users', 'deactivate_users']
    
    def make_it_staff(self, request, queryset):
        """Add selected users to IT Staff group"""
        group, _ = Group.objects.get_or_create(name='IT Staff')
        count = 0
        for user in queryset:
            user.groups.add(group)
            user.is_staff = True
            user.save()
            count += 1
            AuditLog.objects.create(
                user=request.user,
                action='USER_ROLE_CHANGED',
                target_user=user,
                details={'new_role': 'IT Staff', 'changed_by': request.user.username}
            )
        self.message_user(request, f"{count} users added to IT Staff group.")
    make_it_staff.short_description = "Add selected users to IT Staff"
    
    def make_manager(self, request, queryset):
        """Add selected users to Manager group"""
        group, _ = Group.objects.get_or_create(name='Manager')
        count = 0
        for user in queryset:
            user.groups.add(group)
            user.is_staff = True
            user.save()
            count += 1
            AuditLog.objects.create(
                user=request.user,
                action='USER_ROLE_CHANGED',
                target_user=user,
                details={'new_role': 'Manager', 'changed_by': request.user.username}
            )
        self.message_user(request, f"{count} users added to Manager group.")
    make_manager.short_description = "Add selected users to Manager"
    
    def make_employee(self, request, queryset):
        """Set selected users as employees"""
        count = 0
        for user in queryset:
            try:
                profile = user.profile
                profile.user_type = 'employee'
                profile.save()
                count += 1
            except:
                pass
        self.message_user(request, f"{count} users set as employees.")
    make_employee.short_description = "Set selected users as employees"
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} users activated.")
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} users deactivated.")
    deactivate_users.short_description = "Deactivate selected users"


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# --- GROUP ADMIN WITH UNFOLD ---
admin.site.unregister(Group)

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    filter_horizontal = ('permissions',)
    
    list_display = ['name', 'user_count_display', 'permission_count_display']
    search_fields = ['name']
    
    @display(description="Users", ordering='user_count')
    def user_count_display(self, obj):
        count = obj.user_set.count()
        if count > 0:
            return mark_safe(f'<span style="color: #3B82F6; font-weight: bold;">{count}</span>')
        return '0'
    
    @display(description="Permissions", ordering='permissions_count')
    def permission_count_display(self, obj):
        count = obj.permissions.count()
        if count > 0:
            return mark_safe(f'<span style="color: #10B981; font-weight: bold;">{count}</span>')
        return '0'


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(ModelAdmin):
    list_display = [
        'user', 
        'employee_id', 
        'department', 
        'user_type_display', 
        'position', 
        'is_active',
        'created_at'
    ]
    
    list_filter = ['department', 'user_type', 'is_active']
    search_fields = ['user__username', 'user__email', 'employee_id', 'position']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'employee_id')
        }),
        ('Personal Details', {
            'fields': ('department', 'user_type', 'position')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'office_location')
        }),
        ('Employment Details', {
            'fields': ('hire_date',)
        }),
        ('System Access', {
            'fields': ('is_active', 'last_login_ip')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Filter profiles based on user role"""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        if request.user.groups.filter(name__in=['Manager', 'IT Staff', 'Admin']).exists():
            return qs.filter(user__is_superuser=False)
        
        # Regular users see only their own profile
        return qs.filter(user=request.user)
    
    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly for non-authorized users"""
        readonly = list(self.readonly_fields)
        
        if not request.user.is_superuser:
            if not request.user.groups.filter(name__in=['Manager', 'IT Staff', 'Admin']).exists():
                readonly.extend(['user_type', 'is_active', 'department'])
        
        return readonly
    
    @display(description="User Type")
    def user_type_display(self, obj):
        """Display user type with color coding"""
        colors = {
            'admin': '#EF4444',
            'manager': '#F59E0B',
            'it_staff': '#3B82F6',
            'employee': '#10B981',
        }
        color = colors.get(obj.user_type, '#808080')
        return mark_safe(
            f'<span style="color: {color}; font-weight: bold;">{obj.get_user_type_display() if obj.user_type else "Employee"}</span>'
        )
    
    actions = ['set_as_employee', 'set_as_it_staff', 'set_as_manager']
    
    def set_as_employee(self, request, queryset):
        count = queryset.update(user_type='employee')
        self.message_user(request, f"{count} profiles set as Employee.")
    set_as_employee.short_description = "Set as Employee"
    
    def set_as_it_staff(self, request, queryset):
        count = queryset.update(user_type='it_staff')
        self.message_user(request, f"{count} profiles set as IT Staff.")
    set_as_it_staff.short_description = "Set as IT Staff"
    
    def set_as_manager(self, request, queryset):
        count = queryset.update(user_type='manager')
        self.message_user(request, f"{count} profiles set as Manager.")
    set_as_manager.short_description = "Set as Manager"