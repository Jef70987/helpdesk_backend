from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from gridmortapp.system_models.ticket_models import Ticket, TicketMessage, TicketCategory, TicketPriority, TicketStatus
from gridmortapp.system_models.user_models import EmployeeProfile, Department


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    employee_id = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    ticket_count = serializers.SerializerMethodField()
    open_tickets = serializers.SerializerMethodField()
    resolved_tickets = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name', 
            'department', 'employee_id', 'user_type', 'is_active',
            'ticket_count', 'open_tickets', 'resolved_tickets',
            'date_joined', 'last_login'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_department(self, obj):
        try:
            return obj.profile.department.name if obj.profile.department else None
        except:
            return None
    
    def get_employee_id(self, obj):
        try:
            return obj.profile.employee_id
        except:
            return None
    
    def get_user_type(self, obj):
        try:
            return obj.profile.user_type
        except:
            return 'employee'
    
    def get_ticket_count(self, obj):
        try:
            return Ticket.objects.filter(requestor=obj).count()
        except:
            return 0
    
    def get_open_tickets(self, obj):
        try:
            return Ticket.objects.filter(
                requestor=obj,
                status__status_type__in=['new', 'open', 'in_progress', 'pending_customer', 'pending_third_party']
            ).count()
        except:
            return 0
    
    def get_resolved_tickets(self, obj):
        try:
            return Ticket.objects.filter(
                requestor=obj,
                status__status_type='resolved'
            ).count()
        except:
            return 0


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            raise serializers.ValidationError('Email and password are required')
        
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid email or password')
        
        authenticated_user = authenticate(username=user.username, password=password)
        
        if not authenticated_user:
            raise serializers.ValidationError('Invalid email or password')
        
        if not authenticated_user.is_active:
            raise serializers.ValidationError('Your account is disabled')
        
        data['user'] = authenticated_user
        return data


class TicketStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketStatus
        fields = ['id', 'name', 'status_type', 'color_code']


class TicketPrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketPriority
        fields = ['id', 'name', 'level', 'color_code']


class TicketCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketCategory
        fields = ['id', 'name', 'description']


class TicketMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    sender_name = serializers.SerializerMethodField()
    sender_username = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    ticket_id = serializers.SerializerMethodField()
    ticket = serializers.SerializerMethodField()
    
    class Meta:
        model = TicketMessage
        fields = ['id', 'content', 'created_at', 'author', 'author_name', 'sender_name', 
                  'sender_username', 'is_owner', 'message_type', 'ticket_id', 'ticket']
        read_only_fields = ['created_at']
    
    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return 'System'
    
    def get_sender_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return 'System'
    
    def get_sender_username(self, obj):
        if obj.author:
            return obj.author.username
        return 'system'
    
    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and obj.author:
            return obj.author.id == request.user.id
        return False
    
    def get_ticket_id(self, obj):
        return obj.ticket.id if obj.ticket else None
    
    def get_ticket(self, obj):
        return obj.ticket.id if obj.ticket else None


class TicketListSerializer(serializers.ModelSerializer):
    status_label = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    priority_label = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    requestor_name = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    sla_breached = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = ['id', 'ticket_id', 'title', 'status', 'status_label', 'priority', 
                  'priority_label', 'created_at', 'requestor_name', 'assignee_name', 
                  'category_name', 'urgency', 'ticket_type','sla_breached']
    
    def get_status(self, obj):
        """Return the status_type for filtering (new, open, etc.)"""
        if obj.status:
            return obj.status.status_type
        return 'new'
    
    def get_status_label(self, obj):
        """Return the display name for the status (New, Open, etc.)"""
        if obj.status:
            return obj.status.name
        return 'New'
    
    def get_priority(self, obj):
        """Return the priority level for filtering (1, 2, 3, 4)"""
        if obj.priority:
            return obj.priority.level
        return 3
    
    def get_priority_label(self, obj):
        """Return the display name for priority (Critical, High, etc.)"""
        if obj.priority:
            return obj.priority.name
        return 'Medium'
    
    def get_requestor_name(self, obj):
        return obj.requestor.get_full_name() or obj.requestor.username
    
    def get_assignee_name(self, obj):
        if obj.assignee:
            return obj.assignee.get_full_name() or obj.assignee.username
        return None
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    def get_sla_breached(self, obj):
        return obj.sla_breached


class TicketDetailSerializer(serializers.ModelSerializer):
    status_label = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    priority_label = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    requestor_name = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    messages = TicketMessageSerializer(many=True, read_only=True, context={'request': None})
    sla_breached = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = ['id', 'ticket_id', 'title', 'description', 'status', 'status_label', 
                  'priority', 'priority_label', 'category', 'category_name', 
                  'created_at', 'last_modified_at', 'requestor_name', 'assignee_name', 
                  'urgency', 'ticket_type', 'messages', 'sla_breached']
    
    def get_status(self, obj):
        """Return the status_type for filtering (new, open, etc.)"""
        if obj.status:
            return obj.status.status_type
        return 'new'
    
    def get_status_label(self, obj):
        """Return the display name for the status (New, Open, etc.)"""
        if obj.status:
            return obj.status.name
        return 'New'
    
    def get_priority(self, obj):
        """Return the priority level for filtering (1, 2, 3, 4)"""
        if obj.priority:
            return obj.priority.level
        return 3
    
    def get_priority_label(self, obj):
        """Return the display name for priority (Critical, High, etc.)"""
        if obj.priority:
            return obj.priority.name
        return 'Medium'
    
    def get_requestor_name(self, obj):
        return obj.requestor.get_full_name() or obj.requestor.username
    
    def get_assignee_name(self, obj):
        if obj.assignee:
            return obj.assignee.get_full_name() or obj.assignee.username
        return None
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    def get_sla_breached(self, obj):
        return obj.sla_breached
    
    def to_representation(self, instance):
        """Override to ensure context is passed to nested serializer"""
        data = super().to_representation(instance)
        # Pass request context to nested messages serializer
        if 'messages' in data and hasattr(instance, 'messages'):
            request = self.context.get('request')
            if request:
                message_serializer = TicketMessageSerializer(
                    instance.messages.all(), 
                    many=True, 
                    context={'request': request}
                )
                data['messages'] = message_serializer.data
        return data


class TicketCreateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=TicketCategory.objects.all(),
        required=True,
        allow_null=False
    )
    
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'ticket_type', 'urgency']
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['requestor'] = request.user
        
        # Set default priority if not provided
        if not validated_data.get('priority'):
            try:
                default_priority = TicketPriority.objects.filter(is_active=True).order_by('level').first()
                if default_priority:
                    validated_data['priority'] = default_priority
            except:
                pass
        
        # Set default status if not provided
        if not validated_data.get('status'):
            try:
                default_status = TicketStatus.objects.filter(status_type='new').first()
                if default_status:
                    validated_data['status'] = default_status
            except:
                pass
        
        return super().create(validated_data)