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

class ElectionQuerySet(models.QuerySet):
    def live(self):
        """
        Returns only those elections that:
          - have been approved by an admin, and
          - whose start_date ≤ today ≤ end_date
        """
        today = timezone.now().date()
        return self.filter(
            approval_status=Election.APPROVAL_APPROVED,
            start_date__lte=today,
            end_date__gte=today,
        )

class Election(models.Model):
    # — Admin approval choices —
    APPROVAL_PENDING  = 'Pending'
    APPROVAL_APPROVED = 'Approved'
    APPROVAL_CHOICES = [
        (APPROVAL_PENDING,  'Pending Approval'),
        (APPROVAL_APPROVED, 'Approved'),
    ]

    # — Date-based status labels —
    STATUS_PENDING = 'Pending'
    STATUS_ONGOING = 'Ongoing'
    STATUS_ENDED   = 'Ended'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ONGOING, 'Ongoing'),
        (STATUS_ENDED,   'Ended'),
    ]

    club            = models.ForeignKey('Club', on_delete=models.CASCADE, related_name='elections')
    name            = models.CharField(max_length=200)
    description     = models.TextField(blank=True)
    start_date      = models.DateField()
    end_date        = models.DateField()

    # This field is what your admins flip in Django Admin:
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_CHOICES,
        default=APPROVAL_PENDING,
        help_text="Has an admin approved this election?"
    )

    created_by      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_elections')
    candidates      = models.ManyToManyField('Candidate', related_name='elections', blank=True)

    # Swap in our custom manager
    objects = ElectionQuerySet.as_manager()

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError("Start date must be on or before end date.")

    def vote_count(self):
        return (
            self.votes
                .values('candidate')
                .annotate(total=Count('candidate'))
                .order_by('-total')
        )

    def get_winner(self):
        vc = self.vote_count()
        if not vc:
            return "No votes cast"
        winner_id = vc[0]['candidate']
        try:
            cand = self.candidates.get(id=winner_id)
            return cand.user.get_full_name() or cand.user.username
        except Candidate.DoesNotExist:
            return "Error: Winner not found"

    @property
    def date_status(self):
        """
        Returns one of 'Pending', 'Ongoing', 'Ended'
        based on (a) whether it's approved and (b) today's date.
        """
        today = timezone.now().date()

        # Not approved → still pending
        if self.approval_status != self.APPROVAL_APPROVED:
            return self.STATUS_PENDING

        # Approved but hasn't started
        if today < self.start_date:
            return self.STATUS_PENDING

        # In its running window
        if today <= self.end_date:
            return self.STATUS_ONGOING

        # Past end
        return self.STATUS_ENDED

    @property
    def management_status(self):
        """
        Returns one of:
          - "Pending Approval" – Submitted, waiting for an admin to OK it
          - "Scheduled"        – Approved and on the calendar, but not yet started
          - "In Progress"      – Between start_date and end_date
          - "Closed"           – After the end date
        """
        today = timezone.now().date()

        # 1) Submitted, awaiting admin approval
        if self.approval_status == self.APPROVAL_PENDING:
            return "Pending Approval"

        # 2) Approved but hasn't started yet
        if today < self.start_date:
            return "Scheduled"

        # 3) Ongoing window
        if today <= self.end_date:
            return "In Progress"

        # 4) Past end
        return "Closed"
    


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