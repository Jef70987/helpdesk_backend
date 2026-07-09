from django.urls import path
from gridmortapp.views.agent_views import (
    AgentDashboardView,
    AgentTicketListView,
    AgentTicketDetailView,
    AgentMessageView,
    AgentMessagesListView,
    AgentNotificationsView,
    AgentMarkNotificationReadView,
    AgentMarkAllNotificationsReadView,
)

urlpatterns = [
    # Dashboard
    path('dashboard/', AgentDashboardView.as_view(), name='agent_dashboard'),
    
    # Tickets
    path('tickets/', AgentTicketListView.as_view(), name='agent_tickets'),
    path('tickets/<int:pk>/', AgentTicketDetailView.as_view(), name='agent_ticket_detail'),
    
    # Messages
    path('tickets/<int:pk>/messages/', AgentMessageView.as_view(), name='agent_ticket_messages'),
    path('messages/', AgentMessagesListView.as_view(), name='agent_messages'),
    
    # Notifications
    path('notifications/', AgentNotificationsView.as_view(), name='agent_notifications'),
    path('notifications/<int:pk>/read/', AgentMarkNotificationReadView.as_view(), name='agent_notification_read'),
    path('notifications/mark-all-read/', AgentMarkAllNotificationsReadView.as_view(), name='agent_notifications_mark_all_read'),
]