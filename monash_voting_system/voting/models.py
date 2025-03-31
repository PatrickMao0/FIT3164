from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist

# Club represents a university club.
class Club(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'club')  # prevents duplicate memberships

    def __str__(self):
        return f"{self.user.username} in {self.club.name}"

# Election represents an election event hosted by a club.
class Election(models.Model):
    STATUS_PENDING = 'Pending'
    STATUS_ONGOING = 'Ongoing'
    STATUS_ENDED = 'Ended'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ONGOING, 'Ongoing'),
        (STATUS_ENDED, 'Ended'),
    ]
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='elections')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_elections')
    
    def __str__(self):
        return self.name

    def vote_count(self):
        """
        Returns a queryset with vote counts per candidate for this election.
        Example output: [{'candidate': 1, 'total': 5}, {'candidate': 2, 'total': 3}, ...]
        """
        return self.votes.values('candidate').annotate(total=Count('candidate')).order_by('-total')

    def get_winner(self):
        vote_counts = self.vote_count()
        if vote_counts:
            winner_candidate_id = vote_counts[0]['candidate']
            try:
                winner_candidate = self.candidates.get(id=winner_candidate_id)
                full_name = winner_candidate.user.get_full_name()
                return full_name if full_name else winner_candidate.user.username
            except ObjectDoesNotExist:
                # In a robust system, this should not happen if the election is ended.
                return "Error: Winner not found"
        # If there are no votes, you might choose to raise an error or handle it as needed.
        return "No votes cast"




# Candidate represents a candidate running in an election.
class Candidate(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    # Every candidate must be a registered user.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='candidate_entries')
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='candidates/', blank=True, null=True)
    
    def __str__(self):
        return self.user.username

# Vote represents a vote cast for a candidate in an election.
class Vote(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='votes')
    # Record the voter for audit purposes; leave as null if you want to support anonymous voting.
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='votes_cast')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Vote for {self.candidate.user.username} in {self.election.name}"
