from django.urls import path
from gridmortapp.views.ticket_views import (
    LoginView, LogoutView, UserView, RefreshTokenView,
    TicketListView, TicketCreateView, TicketDetailView,
    TicketMessageView, TicketStatsView, RecentTicketsView,
    TicketCategoriesView, MessagesView, NotificationListView, NotificationCountView
)

app_name = 'api'

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/user/', UserView.as_view(), name='user'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='refresh'),
    
    path('tickets/', TicketListView.as_view(), name='ticket_list'),
    path('tickets/create/', TicketCreateView.as_view(), name='ticket_create'),
    path('tickets/<int:pk>/', TicketDetailView.as_view(), name='ticket_detail'),
    path('tickets/<int:pk>/messages/', TicketMessageView.as_view(), name='ticket_message'),
    path('tickets/stats/', TicketStatsView.as_view(), name='ticket_stats'),
    path('tickets/recent/', RecentTicketsView.as_view(), name='ticket_recent'),
    path('tickets/categories/', TicketCategoriesView.as_view(), name='ticket_categories'),
    
    path('messages/', MessagesView.as_view(), name='messages'),
    
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/count/', NotificationCountView.as_view(), name='notification_count'),
]