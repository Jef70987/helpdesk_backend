# gridmortapp/system_models/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models import Q

from .ticket_models import Ticket, TicketMessage, TicketStatus, TicketPriority
from .audit_models import AuditLog


@receiver(post_save, sender=Ticket)
def auto_manage_ticket(sender, instance, created, **kwargs):
    """Complete auto-management of tickets"""
    
    if created:
        # 1. AUTO-ASSIGN to least busy Support Agent
        support_agents = User.objects.filter(
            Q(groups__name='Support Agents') | 
            Q(groups__name='IT Staff')
        ).distinct()
        
        assigned_user = None
        min_tickets = float('inf')
        
        for agent in support_agents:
            ticket_count = Ticket.objects.filter(
                assignee=agent,
                status__status_type__in=['new', 'open', 'in_progress']
            ).count()
            
            if ticket_count < min_tickets:
                min_tickets = ticket_count
                assigned_user = agent
        
        if assigned_user:
            instance.assignee = assigned_user
            instance.first_assignment_at = timezone.now()
        
        # 2. AUTO-SET PRIORITY based on ticket type and urgency
        if instance.urgency:
            # Urgent tickets get High priority
            priority = TicketPriority.objects.get(level=4)
        elif instance.ticket_type in ['incident', 'problem']:
            priority = TicketPriority.objects.get(level=3)  # Medium
        elif instance.ticket_type == 'question':
            priority = TicketPriority.objects.get(level=2)  # Low
        elif instance.ticket_type == 'feature_request':
            priority = TicketPriority.objects.get(level=2)  # Low
        else:
            priority = TicketPriority.objects.get(level=3)  # Medium
        
        instance.priority = priority
        
        # 3. AUTO-SET STATUS to Open (since it's assigned)
        try:
            open_status = TicketStatus.objects.get(status_type='open')
            instance.status = open_status
        except TicketStatus.DoesNotExist:
            pass
        
        instance.save()
        
        # 4. AUTO-CREATE system message
        TicketMessage.objects.create(
            ticket=instance,
            author=assigned_user,
            message_type='system',
            content=f'Ticket automatically assigned to {assigned_user.get_full_name() or assigned_user.username} with {priority.name} priority'
        )
        
        AuditLog.objects.create(
            ticket=instance,
            user=assigned_user,
            action='TICKET_AUTO_ASSIGNED',
            details={
                'ticket_id': instance.ticket_id,
                'assignee': assigned_user.username,
                'priority': priority.name,
                'auto_assigned': True
            }
        )
    
    # 4. AUTO-UPDATE STATUS based on messages
    elif not created:
        # Check if ticket has messages (response)
        if instance.messages.filter(message_type='public').exists():
            # If public message exists, status should be In Progress
            if instance.status.status_type == 'open':
                try:
                    in_progress = TicketStatus.objects.get(status_type='in_progress')
                    instance.status = in_progress
                    instance.save(update_fields=['status'])
                    
                    TicketMessage.objects.create(
                        ticket=instance,
                        author=None,
                        message_type='system',
                        content='Status auto-updated to In Progress'
                    )
                except TicketStatus.DoesNotExist:
                    pass


@receiver(post_save, sender=TicketMessage)
def auto_update_status_on_message(sender, instance, created, **kwargs):
    """Auto-update ticket status when messages are added"""
    if created and instance.ticket:
        ticket = instance.ticket
        
        # If public message from support agent, status -> In Progress
        if instance.message_type == 'public':
            is_support = instance.author.groups.filter(
                Q(name='Support Agents') | Q(name='IT Staff')
            ).exists() if instance.author else False
            
            if is_support:
                if ticket.status.status_type in ['new', 'open']:
                    try:
                        in_progress = TicketStatus.objects.get(status_type='in_progress')
                        ticket.status = in_progress
                        ticket.save(update_fields=['status'])
                        
                        AuditLog.objects.create(
                            ticket=ticket,
                            user=instance.author,
                            action='STATUS_AUTO_UPDATED',
                            details={
                                'ticket_id': ticket.ticket_id,
                                'new_status': 'In Progress',
                                'reason': 'Support agent responded'
                            }
                        )
                    except TicketStatus.DoesNotExist:
                        pass
        
        # If internal note, just log it, no status change


@receiver(pre_save, sender=Ticket)
def auto_resolve_ticket(sender, instance, **kwargs):
    """Auto-resolve ticket when certain conditions are met"""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            
            # Auto-resolve if ticket has been In Progress for > 24 hours
            # and has at least one response
            if instance.status and instance.status.status_type == 'in_progress':
                if instance.first_response_at:
                    time_since_response = (timezone.now() - instance.first_response_at).total_seconds() / 3600
                    
                    # If response was more than 24 hours ago and no new activity
                    if time_since_response > 24:
                        if not instance.messages.filter(created_at__gt=instance.first_response_at).exists():
                            try:
                                resolved = TicketStatus.objects.get(status_type='resolved')
                                instance.status = resolved
                                instance.resolved_at = timezone.now()
                                
                                TicketMessage.objects.create(
                                    ticket=instance,
                                    author=None,
                                    message_type='system',
                                    content='Ticket auto-resolved after 24 hours of inactivity'
                                )
                            except TicketStatus.DoesNotExist:
                                pass
            
            # Auto-close if resolved for > 7 days
            if instance.status and instance.status.status_type == 'resolved':
                if instance.resolved_at:
                    time_since_resolved = (timezone.now() - instance.resolved_at).total_seconds() / 86400  # days
                    
                    if time_since_resolved > 7:
                        try:
                            closed = TicketStatus.objects.get(status_type='closed')
                            instance.status = closed
                            instance.closed_at = timezone.now()
                            
                            TicketMessage.objects.create(
                                ticket=instance,
                                author=None,
                                message_type='system',
                                content='Ticket auto-closed after 7 days of being resolved'
                            )
                        except TicketStatus.DoesNotExist:
                            pass
                            
        except sender.DoesNotExist:
            pass