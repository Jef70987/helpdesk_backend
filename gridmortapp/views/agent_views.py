from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging

from gridmortapp.system_models.ticket_models import Ticket, TicketMessage, TicketCategory, TicketStatus
from gridmortapp.system_models.audit_models import AuditLog
from gridmortapp.serializers.app_serializers import (
    TicketListSerializer, TicketDetailSerializer, TicketMessageSerializer
)

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class AgentDashboardView(APIView):
    """Get agent dashboard statistics and data"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Check if user is an agent
        if not self.is_agent(user):
            return Response(
                {'error': 'Access denied. Agent privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get tickets assigned to this agent
        tickets = Ticket.objects.filter(assignee=user)
        
        # Statistics
        total = tickets.count()
        in_progress = tickets.filter(status__status_type='in_progress').count()
        resolved = tickets.filter(status__status_type='resolved').count()
        closed = tickets.filter(status__status_type='closed').count()
        new = tickets.filter(status__status_type='new').count()
        open_tickets = tickets.filter(status__status_type='open').count()
        pending_customer = tickets.filter(status__status_type='pending_customer').count()
        pending_third_party = tickets.filter(status__status_type='pending_third_party').count()
        
        # SLA Status Breakdown - using sla_breached field from database
        # Breached: tickets with sla_breached = True (regardless of status)
        breached = tickets.filter(sla_breached=True).count()
        
        # At Risk: not breached, open tickets created more than 48 hours ago
        now = timezone.now()
        at_risk = tickets.filter(
            status__status_type__in=['new', 'open', 'in_progress', 'pending_customer', 'pending_third_party'],
            sla_breached=False,
            created_at__lte=now - timezone.timedelta(hours=48)
        ).count()
        
        # In SLA: not breached, open tickets created within last 48 hours
        in_sla = tickets.filter(
            status__status_type__in=['new', 'open', 'in_progress', 'pending_customer', 'pending_third_party'],
            sla_breached=False,
            created_at__gt=now - timezone.timedelta(hours=48)
        ).count()
        
        # SLA Met: resolved or closed tickets that are not breached
        sla_met = tickets.filter(
            status__status_type__in=['resolved', 'closed'],
            sla_breached=False
        ).count()
        
        # Overdue tickets (created more than 48 hours ago, not resolved/closed)
        overdue = tickets.filter(
            status__status_type__in=['new', 'open', 'in_progress', 'pending_customer', 'pending_third_party'],
            created_at__lte=now - timezone.timedelta(hours=48)
        ).count()
        
        # Recent tickets (last 10)
        recent_tickets = tickets.order_by('-created_at')[:10]
        
        # Category breakdown
        category_data = tickets.values('category__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response({
            'stats': {
                'total': total,
                'new': new,
                'open': open_tickets,
                'in_progress': in_progress,
                'pending_customer': pending_customer,
                'pending_third_party': pending_third_party,
                'resolved': resolved,
                'closed': closed,
                'overdue': overdue,
                'at_risk': at_risk,
                'breached': breached,
                'in_sla': in_sla,
                'sla_met': sla_met,
            },
            'recent_tickets': TicketListSerializer(recent_tickets, many=True, context={'request': request}).data,
            'category_breakdown': [
                {'name': item['category__name'] or 'Uncategorized', 'count': item['count']}
                for item in category_data
            ]
        })

    def is_agent(self, user):
        """Check if user is an agent"""
        if user.is_superuser:
            return True
        return user.groups.filter(name='Support Agents').exists() or user.groups.filter(name='IT Staff').exists()

@method_decorator(csrf_exempt, name='dispatch')
class AgentTicketListView(APIView):
    """Get all tickets assigned to the agent with filters"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if not self.is_agent(user):
            return Response(
                {'error': 'Access denied. Agent privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        
        tickets = Ticket.objects.filter(assignee=user)
        
        if status_filter:
            tickets = tickets.filter(status__status_type=status_filter)
        
        if search:
            tickets = tickets.filter(
                Q(ticket_id__icontains=search) |
                Q(title__icontains=search) |
                Q(requestor__username__icontains=search) |
                Q(requestor__email__icontains=search)
            )
        
        tickets = tickets.order_by('-created_at')
        
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_tickets = tickets[start:end]
        serializer = TicketListSerializer(paginated_tickets, many=True, context={'request': request})
        
        return Response({
            'results': serializer.data,
            'count': tickets.count(),
            'page': page,
            'page_size': page_size
        })

    def is_agent(self, user):
        if user.is_superuser:
            return True
        return user.groups.filter(name='Support Agents').exists() or user.groups.filter(name='IT Staff').exists()


@method_decorator(csrf_exempt, name='dispatch')
class AgentTicketDetailView(APIView):
    """Get, update ticket details for agent"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        
        if not self.is_agent(user):
            return Response(
                {'error': 'Access denied. Agent privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            ticket = Ticket.objects.get(pk=pk, assignee=user)
            serializer = TicketDetailSerializer(ticket, context={'request': request})
            return Response(serializer.data)
        except Ticket.DoesNotExist:
            return Response(
                {'error': 'Ticket not found or not assigned to you'},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, pk):
        user = request.user
        
        if not self.is_agent(user):
            return Response(
                {'error': 'Access denied. Agent privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            ticket = Ticket.objects.get(pk=pk, assignee=user)
        except Ticket.DoesNotExist:
            return Response(
                {'error': 'Ticket not found or not assigned to you'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        status_type = request.data.get('status')
        if status_type:
            try:
                status_obj = TicketStatus.objects.get(status_type=status_type)
                ticket.status = status_obj
                
                # Track resolution
                if status_type in ['resolved', 'closed'] and not ticket.resolved_at:
                    ticket.resolved_at = timezone.now()
                
                ticket.save()
                
                AuditLog.objects.create(
                    ticket=ticket,
                    user=user,
                    action='TICKET_UPDATED',
                    details={
                        'status': status_type,
                        'updated_by': user.username,
                        'ticket_id': ticket.ticket_id
                    }
                )
                
                return Response({
                    'success': True,
                    'message': f'Ticket status updated to {status_obj.name}',
                    'status': status_type
                })
            except TicketStatus.DoesNotExist:
                return Response(
                    {'error': 'Invalid status provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {'error': 'No valid fields to update'},
            status=status.HTTP_400_BAD_REQUEST
        )

    def is_agent(self, user):
        if user.is_superuser:
            return True
        return user.groups.filter(name='Support Agents').exists() or user.groups.filter(name='IT Staff').exists()


@method_decorator(csrf_exempt, name='dispatch')
class AgentMessageView(APIView):
    """Get messages and send messages for agent's assigned tickets"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        
        if not self.is_agent(user):
            return Response(
                {'error': 'Access denied. Agent privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            ticket = Ticket.objects.get(pk=pk, assignee=user)
            messages = ticket.messages.all().order_by('created_at')
            serializer = TicketMessageSerializer(messages, many=True, context={'request': request})
            return Response(serializer.data)
        except Ticket.DoesNotExist:
            return Response(
                {'error': 'Ticket not found or not assigned to you'},
                status=status.HTTP_404_NOT_FOUND
            )

    def post(self, request, pk):
        user = request.user
        
        if not self.is_agent(user):
            return Response(
                {'error': 'Access denied. Agent privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            ticket = Ticket.objects.get(pk=pk, assignee=user)
        except Ticket.DoesNotExist:
            return Response(
                {'error': 'Ticket not found or not assigned to you'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        content = request.data.get('content')
        if not content:
            return Response(
                {'error': 'Message content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = TicketMessage.objects.create(
            ticket=ticket,
            author=user,
            content=content,
            message_type='public'
        )
        
        ticket.last_modified_at = timezone.now()
        ticket.save()
        
        AuditLog.objects.create(
            ticket=ticket,
            user=user,
            action='MESSAGE_ADDED',
            details={
                'ticket_id': ticket.ticket_id,
                'message_id': message.id,
                'sent_by': user.username
            }
        )
        
        serializer = TicketMessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def is_agent(self, user):
        if user.is_superuser:
            return True
        return user.groups.filter(name='Support Agents').exists() or user.groups.filter(name='IT Staff').exists()


@method_decorator(csrf_exempt, name='dispatch')
class AgentMessagesListView(APIView):
    """Get all messages from tickets assigned to the agent"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if not self.is_agent(user):
            return Response(
                {'error': 'Access denied. Agent privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tickets = Ticket.objects.filter(assignee=user)
        messages = TicketMessage.objects.filter(
            ticket__in=tickets
        ).order_by('-created_at')[:50]
        
        serializer = TicketMessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

    def is_agent(self, user):
        if user.is_superuser:
            return True
        return user.groups.filter(name='Support Agents').exists() or user.groups.filter(name='IT Staff').exists()


@method_decorator(csrf_exempt, name='dispatch')
class AgentNotificationsView(APIView):
    """Get notifications for agent (messages from customers on assigned tickets)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if not self.is_agent(user):
            return Response(
                {'error': 'Access denied. Agent privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tickets = Ticket.objects.filter(assignee=user)
        notifications = TicketMessage.objects.filter(
            ticket__in=tickets
        ).exclude(author=user).order_by('-created_at')[:20]
        
        # Format notifications
        result = []
        for msg in notifications:
            result.append({
                'id': msg.id,
                'type': 'message_received',
                'message': f'New message from {msg.author.get_full_name() or msg.author.username} on ticket {msg.ticket.ticket_id}',
                'ticket_id': msg.ticket.id,
                'created_at': msg.created_at,
                'read': False,  # This would need a Notification model to track read status
            })
        
        return Response(result)

    def is_agent(self, user):
        if user.is_superuser:
            return True
        return user.groups.filter(name='Support Agents').exists() or user.groups.filter(name='IT Staff').exists()


@method_decorator(csrf_exempt, name='dispatch')
class AgentMarkNotificationReadView(APIView):
    """Mark notification as read (placeholder - would need Notification model)"""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        return Response({'success': True, 'message': 'Notification marked as read'})

    def is_agent(self, user):
        if user.is_superuser:
            return True
        return user.groups.filter(name='Support Agents').exists() or user.groups.filter(name='IT Staff').exists()


@method_decorator(csrf_exempt, name='dispatch')
class AgentMarkAllNotificationsReadView(APIView):
    """Mark all notifications as read (placeholder - would need Notification model)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return Response({'success': True, 'message': 'All notifications marked as read'})

    def is_agent(self, user):
        if user.is_superuser:
            return True
        return user.groups.filter(name='Support Agents').exists() or user.groups.filter(name='IT Staff').exists()