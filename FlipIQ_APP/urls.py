from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('create-deck/', views.create_deck, name='create_deck'),
    path('publish_deck/', views.publish_deck, name='publish_deck'),
    path('deck/edit/<int:deck_id>/', views.edit_deck, name='edit_deck'),
    path('deck/delete/<int:deck_id>/', views.delete_deck, name='delete_deck'),
    path('get-deck-data/<int:deck_id>/', views.get_deck_data, name='get_deck_data'),
    path('deck/<int:deck_id>/', views.control_panel_deck, name='control_panel_decks'),
    path('update_card/<int:card_id>/', views.update_card, name='update_card'),
    path('deck/<int:deck_id>/start_session/', views.start_session, name='start_session'),
    path('deck/<int:deck_id>/end_session/', views.end_session, name='end_session'),
    path('deck/<int:deck_id>/status/', views.get_session_status, name='get_session_status'),
    path('kick_participant/<int:participant_id>/', views.kick_participant, name='kick_participant'),
    path('join_by_code/', views.join_deck_by_code, name='join_by_code'),
    path('join/', views.join_deck_page, name='join_deck_page'),
    path('start_session/<int:session_id>/', views.start_session, name='start_session'),
    path('check_session/<str:code>/', views.check_session_status, name='check_session_status'),

    path('deck/<int:deck_id>/waiting/<int:session_id>/', views.join_waiting, name='join_waiting'),

    path('deck/<int:deck_id>/play/<int:session_id>/', views.play_deck, name='play_deck'),

    path('deck/<int:deck_id>/leave/<int:session_id>/', views.leave_deck, name='leave_deck'),
    path('deck/<int:deck_id>/participants/<int:session_id>/', views.get_participants, name='get_participants'),
    
    path('deck/<int:deck_id>/submit_answer/', views.submit_answer, name='submit_answer'),
    path('deck/<int:deck_id>/start_quiz/', views.start_quiz, name='start_quiz'),
    path('deck/<int:deck_id>/report/<int:session_id>/', views.report_view, name='report_view'),
    path('deck/<int:deck_id>/report/', views.report_view, name='report_view'),
    path('deck/<int:deck_id>/activate_flag/', views.activate_flag, name='activate_flag'),
    path('check_session/<str:code>/', views.check_session_status, name="check_session_status"),
    path('deck/<int:deck_id>/status/', views.deck_status, name='deck_status'),
    path('deck/<int:deck_id>/result/<int:session_id>/', views.deck_result, name='deck_result'),
    path('deck/<int:deck_id>/reset_progress/<int:session_id>/', views.reset_progress, name='reset_progress'),
    path('deck/<int:deck_id>/not_started/', views.deck_not_started, name='deck_not_started'),
]
