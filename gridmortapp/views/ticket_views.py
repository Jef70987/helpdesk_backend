from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
import logging

from gridmortapp.system_models.ticket_models import Ticket, TicketMessage, TicketCategory, TicketStatus, TicketPriority
from gridmortapp.system_models.audit_models import AuditLog
from gridmortapp.serializers.app_serializers import (
    LoginSerializer, UserSerializer, TicketListSerializer, 
    TicketDetailSerializer, TicketCreateSerializer,
    TicketMessageSerializer, TicketCategorySerializer
)

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            AuditLog.objects.create(
                user=user,
                action='USER_LOGIN',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                details={'email': user.email}
            )
            
            user_serializer = UserSerializer(user)
            response = Response({
                'success': True,
                'user': user_serializer.data,
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
            
            response.set_cookie(
                'access_token',
                access_token,
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=60 * 60,
                path='/'
            )
            response.set_cookie(
                'refresh_token',
                refresh_token,
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=7 * 24 * 60 * 60,
                path='/'
            )
            
            return response
        
        logger.warning(f"Login failed for email: {request.data.get('username', 'unknown')}")
        
        return Response(
            {'error': 'Invalid email or password'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        AuditLog.objects.create(
            user=request.user,
            action='USER_LOGOUT',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
        
        response = Response({'success': True, 'message': 'Logout successful'})
        response.delete_cookie('access_token', path='/')
        response.delete_cookie('refresh_token', path='/')
        return response


@method_decorator(csrf_exempt, name='dispatch')
class UserView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class RefreshTokenView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            return Response(
                {'error': 'Session expired. Please login again.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            
            response = Response({'success': True})
            response.set_cookie(
                'access_token',
                access_token,
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=60 * 60,
                path='/'
            )
            return response
        except Exception as e:
            logger.error(f"Refresh token error: {str(e)}")
            return Response(
                {'error': 'Session expired. Please login again.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )


@method_decorator(csrf_exempt, name='dispatch')
class TicketListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        status_filter = request.query_params.get('status')
        
        tickets = Ticket.objects.filter(requestor=request.user)
        
        if status_filter:
            tickets = tickets.filter(status__status_type=status_filter)
        
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


@method_decorator(csrf_exempt, name='dispatch')
class TicketCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = TicketCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            ticket = serializer.save()
            
            AuditLog.objects.create(
                user=request.user,
                action='TICKET_CREATED',
                ticket=ticket,
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'ticket_id': ticket.ticket_id}
            )
            
            return Response({
                'success': True,
                'message': 'Ticket created successfully',
                'id': ticket.id,
                'ticket_id': ticket.ticket_id
            }, status=status.HTTP_201_CREATED)
        
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class TicketDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            ticket = Ticket.objects.get(pk=pk, requestor=request.user)
            serializer = TicketDetailSerializer(ticket, context={'request': request})
            return Response(serializer.data)
        except Ticket.DoesNotExist:
            return Response(
                {'error': 'Ticket not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


@method_decorator(csrf_exempt, name='dispatch')
class TicketMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        """Get messages for a specific ticket"""
        try:
            ticket = Ticket.objects.get(pk=pk, requestor=request.user)
            messages = ticket.messages.all()
            serializer = TicketMessageSerializer(messages, many=True, context={'request': request})
            return Response(serializer.data)
        except Ticket.DoesNotExist:
            return Response(
                {'error': 'Ticket not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def post(self, request, pk):
        try:
            ticket = Ticket.objects.get(pk=pk, requestor=request.user)
        except Ticket.DoesNotExist:
            return Response(
                {'error': 'Ticket not found'}, 
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
            author=request.user,
            content=content,
            message_type='public'
        )
        
        ticket.last_modified_at = timezone.now()
        ticket.save()
        
        serializer = TicketMessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class TicketStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        tickets = Ticket.objects.filter(requestor=request.user)
        
        total = tickets.count()
        open_count = tickets.filter(status__status_type__in=['new', 'open', 'in_progress', 'pending_customer', 'pending_third_party']).count()
        resolved_count = tickets.filter(status__status_type='resolved').count()
        closed_count = tickets.filter(status__status_type='closed').count()
        
        return Response({
            'total': total,
            'open': open_count,
            'resolved': resolved_count,
            'closed': closed_count
        })


@method_decorator(csrf_exempt, name='dispatch')
class RecentTicketsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        tickets = Ticket.objects.filter(requestor=request.user).order_by('-created_at')[:5]
        serializer = TicketListSerializer(tickets, many=True, context={'request': request})
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class TicketCategoriesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        categories = TicketCategory.objects.filter(is_active=True, parent__isnull=True)
        serializer = TicketCategorySerializer(categories, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class MessagesView(APIView):
    """Get all messages from user's tickets"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        tickets = Ticket.objects.filter(requestor=request.user)
        messages = TicketMessage.objects.filter(
            ticket__in=tickets
        ).order_by('-created_at')[:50]
        
        serializer = TicketMessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class NotificationListView(APIView):
    """Get notifications (messages where user is not the author)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        tickets = Ticket.objects.filter(requestor=request.user)
        messages = TicketMessage.objects.filter(
            ticket__in=tickets
        ).exclude(author=request.user).order_by('-created_at')[:20]
        
        serializer = TicketMessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class NotificationCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        tickets = Ticket.objects.filter(requestor=request.user)
        count = TicketMessage.objects.filter(
            ticket__in=tickets
        ).exclude(author=request.user).count()
        
        return Response({'count': count})