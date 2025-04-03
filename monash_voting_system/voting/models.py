from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist, ValidationError

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
    
    club = models.ForeignKey('Club', on_delete=models.CASCADE, related_name='elections')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_elections')
    # New field: candidates contesting in this election.
    candidates = models.ManyToManyField('Candidate', related_name='elections', blank=True)

    
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
    
    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError("Start date must be before end date.")



# Candidate represents a candidate running in an election.
class Candidate(models.Model):
    club = models.ForeignKey('Club', on_delete=models.CASCADE, related_name='candidates')
    # Every candidate must be a registered user.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='candidate_entries')
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='candidates/', blank=True, null=True)
    
    class Meta:
        unique_together = ('club', 'user')
        
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



class UserProfile(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    FACULTY_CHOICES = (
        ('ADA', 'Art, Design and Architecture'),
        ('ART', 'Arts'),
        ('BUS', 'Business and Economics'),
        ('EDU', 'Education'),
        ('ENG', 'Engineering'),
        ('IT', 'Information Technology'),
        ('LAW', 'Law'),
        ('MED', 'Medicine, Nursing and Health Sciences'),
        ('PHAR', 'Pharmacy and Pharmaceutical Sciences'),
        ('SCI', 'Science'),
    )
    
    # Only two options: Undergraduate and Postgraduate (with PhD as a subtype of PG)
    LEVEL_CHOICES = (
        ('UG', 'Undergraduate'),
        ('PG', 'Postgraduate'),
    )
    
    # New field to identify if the user is a student or staff
    ROLE_CHOICES = (
        ('STUDENT', 'Student'),
        ('STAFF', 'Staff'),
    )
    
    CAMPUS_CHOICES = (
        ('CLAYTON', 'Clayton'),
        ('CAULFIELD', 'Caulfield'),
        ('PENINSULA', 'Peninsula'),
        ('PARKVILLE', 'Parkville'),
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    faculty = models.CharField(max_length=4, choices=FACULTY_CHOICES, blank=True)
    level_of_education = models.CharField(max_length=2, choices=LEVEL_CHOICES, blank=True)
    campus_location = models.CharField(max_length=10, choices=CAMPUS_CHOICES, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STUDENT')
    
    def __str__(self):
        return f"Profile for {self.user.username}"