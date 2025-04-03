from django.contrib import admin
from .models import Club, Election, Candidate, Vote, Membership, UserProfile

admin.site.register(Club)
admin.site.register(Election)
admin.site.register(Candidate)
admin.site.register(Vote)
admin.site.register(Membership)
admin.site.register(UserProfile)