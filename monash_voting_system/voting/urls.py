from django.urls import path
from . import views
from .views import update_election,create_election,vote_stats_view

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('clubs/', views.club_selection_view, name='club_selection'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('user-request/',      views.user_request,       name='user_request'),
    path('vote/<int:election_id>/', views.voting_view, name='voting'),
    path('trail-detail/', views.trail_detail_view, name='trail_detail'),

    path('election/create/', create_election, name='create_election'),
    path('election/update/', views.update_election, name='update_election'),
    path('add-candidate/', views.add_candidate, name='add_candidate'),
    path('stats/<int:election_id>/', views.vote_stats_view, name='vote_stats'),
]

