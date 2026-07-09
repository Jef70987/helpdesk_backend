# gridmortapp/models.py
from django.db import models

# Exposing all models from the models folder
from .system_models.ticket_models import (
    TicketCategory,
    TicketPriority,
    TicketStatus,
    Ticket,
    TicketMessage,
)

from .system_models.user_models import (
    Department,
    EmployeeProfile
)

from .system_models.inventory_models import (
    HardwareCategory,
    HardwareItem,
    InventoryMovement
)

from .system_models.report_models import (
    ReportType,
    Report,
    ReportLog
)

from .system_models.audit_models import (
    AuditLog
)

__all__ = [
    # Ticket models
    'TicketCategory',
    'TicketPriority', 
    'TicketStatus',
    'Ticket',
    'TicketMessage',
    
    # User models
    'Department',
    'EmployeeProfile',
    
    # Inventory models
    'HardwareCategory',
    'HardwareItem',
    'InventoryMovement',
    
    # Report models
    'ReportType',
    'Report',
    'ReportLog',
    
    # Audit models
    'AuditLog',
]