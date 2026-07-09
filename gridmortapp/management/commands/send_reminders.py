# gridmortapp/management/commands/send_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from django.db.models import Q, Count

from gridmortapp.system_models.ticket_models import Ticket, TicketMessage, TicketStatus
from gridmortapp.system_models.audit_models import AuditLog


class Command(BaseCommand):
    help = 'Send reminder notifications for unassigned or unattended tickets'

    def handle(self, *args, **options):
        self.stdout.write("Checking for tickets that need reminders...")
        
        now = timezone.now()
        reminders_sent = 0
        
        # 1. Tickets that are NEW and unassigned for more than 10 minutes
        new_tickets = Ticket.objects.filter(
            status__status_type='new',
            assignee__isnull=True,
            created_at__lte=now - timedelta(minutes=10)
        )
        
        for ticket in new_tickets:
            # Send notification to IT Staff group
            it_staff = User.objects.filter(groups__name='IT Staff')
            
            for staff in it_staff:
                # Create notification message (visible to IT Staff only)
                TicketMessage.objects.create(
                    ticket=ticket,
                    author=None,
                    message_type='internal',
                    content=f'[URGENT] Ticket {ticket.ticket_id} has been waiting for assignment for {self.get_wait_time(ticket.created_at)} minutes. Please assign immediately!'
                )
                
                # Log reminder
                AuditLog.objects.create(
                    ticket=ticket,
                    action='TICKET_REMINDER_SENT',
                    details={
                        'ticket_id': ticket.ticket_id,
                        'type': 'assignment_reminder',
                        'recipient': staff.username,
                        'wait_time_minutes': (now - ticket.created_at).total_seconds() / 60
                    }
                )
            
            # Update notification tracking
            ticket.last_notification_at = now
            ticket.notification_count += 1
            ticket.save()
            reminders_sent += 1
            
            self.stdout.write(f"Sent assignment reminder for {ticket.ticket_id}")
        
        # 2. Tickets that are OPEN/IN_PROGRESS with no response for more than 30 minutes
        assigned_tickets = Ticket.objects.filter(
            Q(status__status_type='open') | Q(status__status_type='in_progress'),
            assignee__isnull=False,
            last_modified_at__lte=now - timedelta(minutes=30)
        ).exclude(
            last_notification_at__gte=now - timedelta(minutes=10)  # Don't spam
        )
        
        for ticket in assigned_tickets:
            # Send reminder to assignee
            if ticket.assignee:
                TicketMessage.objects.create(
                    ticket=ticket,
                    author=None,
                    message_type='internal',
                    content=f'[REMINDER] Ticket {ticket.ticket_id} has been assigned to you for {self.get_wait_time(ticket.last_modified_at)} minutes. Please provide an update.'
                )
                
                AuditLog.objects.create(
                    ticket=ticket,
                    action='TICKET_REMINDER_SENT',
                    details={
                        'ticket_id': ticket.ticket_id,
                        'type': 'response_reminder',
                        'recipient': ticket.assignee.username,
                        'last_update_minutes': (now - ticket.last_modified_at).total_seconds() / 60
                    }
                )
                
                ticket.last_notification_at = now
                ticket.notification_count += 1
                ticket.response_reminder_count += 1
                ticket.save()
                reminders_sent += 1
                
                self.stdout.write(f"Sent response reminder to {ticket.assignee.username} for {ticket.ticket_id}")
        
        # 3. Check SLA breaches - tickets approaching deadline
        tickets_to_check = Ticket.objects.filter(
            status__status_type__in=['new', 'open', 'in_progress'],
            priority__isnull=False,
            sla_breached=False
        )
        
        for ticket in tickets_to_check:
            sla_status = ticket.calculate_sla_status()
            if sla_status:
                # Response SLA
                if sla_status['response']['deadline']:
                    percentage_used = (sla_status['response']['elapsed'] / sla_status['response']['deadline']) * 100
                    if percentage_used > 80:  # Over 80% of SLA time used
                        warning_level = '[WARNING]' if percentage_used < 95 else '[URGENT]'
                        
                        TicketMessage.objects.create(
                            ticket=ticket,
                            author=None,
                            message_type='internal',
                            content=f'{warning_level}: Ticket {ticket.ticket_id} is approaching SLA deadline! {int(percentage_used)}% of response time used.'
                        )
                        
                        # Escalate if over 95%
                        if percentage_used > 95 and ticket.escalation_level < 2:
                            ticket.escalation_level += 1
                            ticket.escalated_at = now
                            ticket.save()
                            
                            TicketMessage.objects.create(
                                ticket=ticket,
                                author=None,
                                message_type='internal',
                                content=f'[ESCALATED] Ticket {ticket.ticket_id} has been auto-escalated to Level {ticket.escalation_level} due to SLA risk.'
                            )
                            
                            AuditLog.objects.create(
                                ticket=ticket,
                                action='TICKET_AUTO_ESCALATED',
                                details={
                                    'ticket_id': ticket.ticket_id,
                                    'new_level': ticket.escalation_level,
                                    'reason': 'SLA risk',
                                    'percentage_used': percentage_used
                                }
                            )
                            
                            reminders_sent += 1
                            self.stdout.write(f"Auto-escalated {ticket.ticket_id} to Level {ticket.escalation_level}")
        
        self.stdout.write(self.style.SUCCESS(f"Sent {reminders_sent} reminders/notifications!"))

    def get_wait_time(self, timestamp):
        """Get human-readable wait time"""
        delta = timezone.now() - timestamp
        minutes = int(delta.total_seconds() / 60)
        
        if minutes < 60:
            return str(minutes)
        else:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m"