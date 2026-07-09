# gridmortapp/admin.py
from gridmortapp.admin_ui.user_admin import DepartmentAdmin, UserAdmin, EmployeeProfileAdmin
from gridmortapp.admin_ui.inventory_admin import HardwareCategoryAdmin, HardwareItemAdmin, InventoryMovementAdmin
from gridmortapp.admin_ui.report_admin import ReportTypeAdmin, ReportAdmin, ReportLogAdmin
from gridmortapp.admin_ui.ticket_admin import TicketCategoryAdmin, TicketPriorityAdmin, TicketStatusAdmin, TicketAdmin
from gridmortapp.admin_ui.audit_admin import AuditLogAdmin
from django.contrib import admin
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.admin import TokenAdmin

# Register Token model with Unfold
admin.site.register(Token, TokenAdmin)

from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin

# 1. Unregister Django's plain default Group admin
admin.site.unregister(Group)

# 2. Re-register it combined with Unfold's ModelAdmin layout
@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    show_add_link = True