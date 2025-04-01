from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Election, Membership, Candidate, Vote, Club
import json
from django.http import JsonResponse
from datetime import datetime
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

@login_required
@user_passes_test(is_club_admin)
def admin_dashboard_view(request):
    clubs = Club.objects.all()
    
    # Build a mapping from club id to list of candidate details (using the new Candidate model)
    club_candidates = {}
    for club in clubs:
        candidates = Candidate.objects.filter(club=club)
        club_candidates[club.id] = [
            {
                'id': candidate.id,
                'username': candidate.user.username,
                'full_name': candidate.user.get_full_name() or candidate.user.username,
            }
            for candidate in candidates
        ]
    
    context = {
        'clubs': clubs,
        'club_candidates_json': json.dumps(club_candidates),
    }
    return render(request, 'voting/admin_dashboard.html', context)


@login_required
@user_passes_test(is_club_admin)
def update_election(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    if request.method == 'POST':
        # Extract data from the POST request.
        election.name = request.POST.get('electionName')
        election.description = request.POST.get('electionDescription')
        election.start_date = request.POST.get('startDate')
        election.end_date = request.POST.get('endDate')
        
        # Update club if needed.
        club_id = request.POST.get('clubName')
        if club_id:
            election.club = get_object_or_404(Club, pk=club_id)
        
        # Update the many-to-many candidates.
        # Remove existing candidates.
        election.candidates.clear()
        # Retrieve the candidate usernames from the select fields.
        candidate_usernames = request.POST.getlist('candidateNames[]')
        for username in candidate_usernames:
            try:
                # Look up the Candidate based on username and club.
                candidate = Candidate.objects.get(user__username=username, club=election.club)
                election.candidates.add(candidate)
            except Candidate.DoesNotExist:
                messages.error(request, f"Candidate '{username}' not found in the selected club.")
        
        # Save the election
        election.save()
        messages.success(request, "Election updated successfully!")
        return redirect('admin_dashboard')  # Adjust as needed
    else:
        # For GET requests, you can pre-populate a form or redirect.
        return render(request, 'voting/edit_election.html', {'election': election})


@login_required
@user_passes_test(is_club_admin)
def create_election(request):
    if request.method == 'POST':
        club_id = request.POST.get('clubName')
        name = request.POST.get('electionName')
        description = request.POST.get('electionDescription')
        start_date_str = request.POST.get('startDate')
        end_date_str = request.POST.get('endDate')
        candidate_usernames = request.POST.getlist('candidateNames[]')
        
        # Validate that the dates are provided
        if not start_date_str or not end_date_str:
            messages.error(request, "Both start and end dates are required.")
            return redirect('admin_dashboard')
        
        # Convert from "DD-MM-YYYY" to a date object
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
            return redirect('admin_dashboard')
                
        club = get_object_or_404(Club, pk=club_id)
        
        # Create the election object
        election = Election.objects.create(
            club=club,
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status=Election.STATUS_PENDING,
            created_by=request.user
        )
        
        # Associate candidates to the election
        for username in candidate_usernames:
            try:
                candidate = Candidate.objects.get(user__username=username, club=club)
                election.candidates.add(candidate)
            except Candidate.DoesNotExist:
                messages.error(request, f"Candidate '{username}' not found for club {club.name}.")
        
        election.save()
        messages.success(request, "Election created successfully!")
        return redirect('admin_dashboard')
    else:
        messages.error(request, "Invalid request.")
        return redirect('admin_dashboard')


def vote_stats_view(request):
    return render(request, 'voting/vote_stats.html')

def trail_detail_view(request):
    return render(request, 'voting/trail_detail.html')



