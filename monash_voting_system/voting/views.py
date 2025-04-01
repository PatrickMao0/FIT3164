from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Election, Membership, Candidate, Vote
import json
from django.http import JsonResponse

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def login_view(request):
    if request.method == "POST":
        # Retrieve username, password, and login type from the form
        username = request.POST.get("username")
        password = request.POST.get("password")
        login_type = request.POST.get("login_type", "normal")  # Default to normal login
        
        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)  # Log the user in (creates session)
            if login_type == "admin":
                # Check if the user is in the "club_admin" group
                if user.groups.filter(name="club_admin").exists():
                    return redirect("admin_dashboard")
                else:
                    messages.error(request, "You are not authorized to log in as admin. Please contact support if you believe this is an error.")
                    # Re-render the login page with the error message
                    return render(request, "voting/login_page.html")
            else:
                # Normal login: redirect to club selection page
                return redirect("club_selection")
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, "voting/login_page.html")
    
    # For GET requests, just display the login page
    return render(request, "voting/login_page.html")



from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Membership, Election

@login_required
def club_selection_view(request):
    # Get all clubs the user has membership in
    membership_clubs = Membership.objects.filter(user=request.user).values_list('club', flat=True)
    print("DEBUG: membership_clubs =", list(membership_clubs))

    # Filter elections for those clubs, but only those that are "Ongoing"
    elections = Election.objects.filter(club__in=membership_clubs, status='Ongoing')
    print("DEBUG: elections =", list(elections))

    # Retrieve previous votes for the clubs the user is a member of
    previous_votes = Vote.objects.filter(
        voter=request.user,
        election__club__in=membership_clubs
    ).select_related('election', 'candidate')

    # Create a list of election IDs that the user has already voted in
    voted_election_ids = list(Vote.objects.filter(voter=request.user).values_list('election_id', flat=True))
    print("DEBUG: voted_election_ids =", voted_election_ids)

    return render(request, 'voting/club_selection_page.html', {
        'elections': elections,
        'previous_votes': previous_votes,
        'voted_election_ids': voted_election_ids,
    })



# Helper function to check if a user belongs to the "club_admin" group.
def is_club_admin(user):
    return user.groups.filter(name='club_admin').exists()

@login_required
@user_passes_test(is_club_admin)
def admin_dashboard_view(request):
    return render(request, 'voting/admin_dashboard.html')

@login_required
def voting_view(request, election_id):
    election = get_object_or_404(Election, id=election_id)

    # Check membership
    if not Membership.objects.filter(user=request.user, club=election.club).exists():
        messages.error(request, "You are not a member of this club and cannot vote here.")
        return redirect('club_selection')

    if request.method == "POST":
        candidate_id = request.POST.get("candidate")
        if not candidate_id:
            return JsonResponse({"success": False, "error": "No candidate selected."}, status=400)
        candidate = get_object_or_404(Candidate, id=candidate_id, election=election)

        # Record the vote
        Vote.objects.create(
            election=election,
            candidate=candidate,
            voter=request.user
        )
        # Return a JSON response indicating success.
        return JsonResponse({"success": True})

    return render(request, "voting/voting_page.html", {"election": election})

def vote_stats_view(request):
    return render(request, 'voting/vote_stats.html')

def trail_detail_view(request):
    return render(request, 'voting/trail_detail.html')



