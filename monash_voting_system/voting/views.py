from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden
from .models import Election, Membership, Candidate, Vote, Club, UserProfile, CandidateForm
from django.utils import timezone


import json
from datetime import datetime
from django.db.models import Count, F, Value, CharField
from django.db.models.functions import Concat, Coalesce,TruncHour
from django.core.mail import mail_admins

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


    # Filter elections for those clubs, but only those that are "Ongoing"
    elections = Election.objects.live().filter(club__in=membership_clubs)

    # Retrieve previous votes for the clubs the user is a member of
    previous_votes = Vote.objects.filter(
        voter=request.user,
        election__club__in=membership_clubs
    ).select_related('election', 'candidate')

    # Create a list of election IDs that the user has already voted in
    voted_election_ids = list(Vote.objects.filter(voter=request.user).values_list('election_id', flat=True))


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
        candidate = get_object_or_404(Candidate, id=candidate_id, club=election.club)

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
    clubs     = Club.objects.all()
    elections = Election.objects.all().order_by('start_date')
    
    for election in elections:
        election.candidate_data = json.dumps([
            {
                'username':  c.user.username,
                'full_name': c.user.get_full_name() or c.user.username,
            }
            for c in election.candidates.all()
        ])
    
    # Build mapping for club candidates for use in candidate select dropdowns.
    club_candidates = {}
    for club in clubs:
        candidates = list(Candidate.objects.filter(club=club))
        club_candidates[club.id] = [
            {
                'id': candidate.id,
                'username': candidate.user.username,
                'full_name': candidate.user.get_full_name() or candidate.user.username,
            }
            for candidate in candidates
        ]
    
    all_candidates = Candidate.objects.select_related('club','user').all()
    
    context = {
        'clubs': clubs,
        'elections': elections,
        'club_candidates_json': json.dumps(club_candidates),
        'candidate_form': CandidateForm(),
        'all_candidates':    all_candidates, 
    }
    return render(request, 'voting/admin_dashboard.html', context)

@login_required
@user_passes_test(is_club_admin)
def update_election(request):
    if request.method == 'POST':
        election_id = request.POST.get('electionId')
        election = get_object_or_404(Election, pk=election_id)
        election.name = request.POST.get('electionName')
        election.description = request.POST.get('electionDescription')
        election.start_date = request.POST.get('startDate')
        election.end_date = request.POST.get('endDate')
        
        
        # Update candidates.
        election.candidates.clear()
        candidate_usernames = request.POST.getlist('candidateNames[]')
        for username in candidate_usernames:
            try:
                candidate = Candidate.objects.get(user__username=username, club=election.club)
                election.candidates.add(candidate)
            except Candidate.DoesNotExist:
                messages.error(request, f"Candidate '{username}' not found for club {election.club.name}.")
        
        election.save()
        messages.success(request, "Election updated successfully!")
        return redirect('admin_dashboard')
    else:
        messages.error(request, "Invalid request.")
        return redirect('admin_dashboard')


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
            approval_status=Election.APPROVAL_PENDING,
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



def _labels_and_counts(queryset, field, choices_dict):
    """
    Return two lists:

      labels -> human-readable names from choices_dict
      data   -> integer counts for each label

    The queryset should already be filtered to the population you
    care about (e.g. all voters in an election).
    """
    counts = (
        queryset
        .values(code=F(field))
        .annotate(total=Count(field))
        .order_by()          # keep DB from auto-ordering by code
    )
    labels = [choices_dict.get(row["code"], "Unknown") for row in counts]
    data   = [row["total"] for row in counts]
    return labels, data




@login_required
@user_passes_test(is_club_admin)
def vote_stats_view(request, election_id):
    election = get_object_or_404(Election, pk=election_id)

    # 1) Voter turnout
    total_members = Membership.objects.filter(club=election.club).count()
    total_votes = (
        Vote.objects
            .filter(election=election)
            .values('voter_id')    # group by voter
            .distinct()
            .count()
    )
    not_voted    = max(total_members - total_votes, 0)
    turnout_data = [total_votes, not_voted]

    # 2) Votes per candidate (full name or fallback to username)
    per_cand = (
        Vote.objects.filter(election=election)
            .values(
                name=Concat(
                    Coalesce('candidate__user__first_name', Value('')),
                    Value(' '),
                    Coalesce('candidate__user__last_name',  Value('')),
                    output_field=CharField()
                ),
                username=F('candidate__user__username')
            )
            .annotate(total=Count('id'))
            .order_by('-total')
    )
    cand_labels = [
        (row['name'].strip() or row['username'])
        for row in per_cand
    ]
    cand_data = [row['total'] for row in per_cand]

    # 3) Gender & category breakdown
    voters = UserProfile.objects.filter(user__votes_cast__election=election).distinct()
    def _labels_and_counts(qs, field, choices):
        cnts = qs.values(code=F(field)).annotate(total=Count(field)).order_by()
        return [dict(choices).get(r['code'],'Unknown') for r in cnts], [r['total'] for r in cnts]

    gender_labels,   gender_data   = _labels_and_counts(voters, "gender",   UserProfile.GENDER_CHOICES)
    category_labels, category_data = _labels_and_counts(voters, "role",     UserProfile.ROLE_CHOICES)

    # 4) Votes by faculty (stacked UG vs PG)
    faculty_labels = []
    ug_counts = []
    pg_counts = []
    for code, label in UserProfile.FACULTY_CHOICES:
        ug = Vote.objects.filter(
            election=election,
            voter__userprofile__faculty=code,
            voter__userprofile__level_of_education='UG'
        ).count()
        pg = Vote.objects.filter(
            election=election,
            voter__userprofile__faculty=code,
            voter__userprofile__level_of_education='PG'
        ).count()
        if ug or pg:
            faculty_labels.append(label)
            ug_counts.append(ug)
            pg_counts.append(pg)
    faculty_stacked = {"labels": faculty_labels, "ug": ug_counts, "pg": pg_counts}

    # 5) Campus turnout
    campus_stats = []
    for code, label in UserProfile.CAMPUS_CHOICES:
        members = Membership.objects.filter(
            club=election.club,
            user__userprofile__campus_location=code
        ).count()
        votes = Vote.objects.filter(
            election=election,
            voter__userprofile__campus_location=code
        ).values('voter_id').distinct().count()
        campus_stats.append({
            "name":     label,
            "voted":    votes,
            "notVoted": max(members - votes, 0),
        })

    # 6) Voting pace – cumulative votes over time (hourly)
    hourly = (
        Vote.objects.filter(election=election)
            .annotate(hour=TruncHour('timestamp'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
    )
    running = 0
    pace_labels = []
    pace_data   = []
    for row in hourly:
        running += row['count']
        pace_labels.append(row['hour'].strftime('%Y-%m-%d %H:%M'))
        pace_data.append(running)

    # Pack everything into one stats dict
    stats = {
        "turnout":      {"labels": ["Voted", "Did Not Vote"], "data": turnout_data},
        "perCandidate": {"labels": cand_labels,               "data": cand_data},
        "gender":       {"labels": gender_labels,             "data": gender_data},
        "category":     {"labels": category_labels,           "data": category_data},
        "faculty":      faculty_stacked,
        "campus":       campus_stats,
        "pace":         {"labels": pace_labels, "data": pace_data},
    }

        # 7) Radar: votes by faculty for each candidate
    radar_labels = [ label for code, label in UserProfile.FACULTY_CHOICES ]

    radar_data = {}
    for row in per_cand:
        username     = row["username"]
        display_name = (row["name"].strip() or username)

        candidate = Candidate.objects.get(
            user__username=username,
            club=election.club
        )

        # count this candidate’s votes in each faculty
        counts = []
        for code, _label in UserProfile.FACULTY_CHOICES:
            c = Vote.objects.filter(
                election=election,
                candidate=candidate,
                voter__userprofile__faculty=code
            ).count()
            counts.append(c)

        radar_data[display_name] = counts

    stats["radar"] = {
        "labels": radar_labels,
        "data":   radar_data,
    }

    return render(request, "voting/vote_stats.html", {
        "election":   election,
        "stats_json": json.dumps(stats),
    })



@login_required
@user_passes_test(is_club_admin)
def user_request(request):
    if request.method == "POST":
        username   = request.POST["username"]
        action     = request.POST["action"]
        reason_code= request.POST["reason_code"]
        reason     = request.POST.get("reason","")
        # build a message or create a model record here…
        subject = f"[User Request] {action.title()} {username}"
        body = (
            f"Requested by {request.user.username}\n\n"
            f"Action: {action}\n"
            f"Username/Email: {username}\n"
            f"Reason Code: {reason_code}\n"
            f"Additional Info: {reason}"
        )
        mail_admins(subject, body)
        messages.success(request, "Your request has been sent to the site admins.")
    return redirect("admin_dashboard")


@login_required
@user_passes_test(is_club_admin)
def add_candidate(request):
    if request.method == 'POST':
        form = CandidateForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            # update existing or create new
            candidate, created = Candidate.objects.update_or_create(
                club=cd['club'],
                user=cd['user'],
                defaults={
                    'bio':   cd['bio'],
                    'photo': cd['photo'],
                }
            )
            if created:
                messages.success(request, f"Candidate {candidate.user.username} added!")
            else:
                messages.success(request, f"Candidate {candidate.user.username} updated!")
        else:
            # show form errors in dashboard
            messages.error(request, "Error adding candidate: " +
                                      "; ".join(f"{f}: {e}" for f,e_list in form.errors.items() for e in e_list))
    # whether GET or POST, go back to dashboard
    return redirect('admin_dashboard')







def trail_detail_view(request):
    return render(request, 'voting/trail_detail.html')



