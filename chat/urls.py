from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('message/', views.chat_message, name='chat_message'),
    path('trigger/', views.fomo_trigger, name='fomo_trigger'),

    # Admin — session management
    path('admin/kanban/', views.kanban_board, name='kanban_board'),
    path('admin/sessions/<uuid:session_id>/', views.session_update, name='session_update'),
    path('admin/sessions/<uuid:session_id>/takeover/', views.takeover_session, name='takeover_session'),
    path('admin/sessions/<uuid:session_id>/release/', views.release_session, name='release_session'),
    path('admin/sessions/<uuid:session_id>/send/', views.admin_send_message, name='admin_send_message'),
]
