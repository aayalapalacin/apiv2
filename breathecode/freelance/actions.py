import os, re
from itertools import chain
from .models import Freelancer, Issue, Bill
from breathecode.authenticate.models import CredentialsGithub
from schema import Schema, And, Use, Optional, SchemaError
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from github import Github


def sync_user_issues(freelancer):
    github_id = freelancer.github_user.github_id
    credentials = CredentialsGithub.objects.filter(github_id=github_id).first()
    if credentials is None:
        raise ValueError(f"Credentials for this user {gitub_user_id} not found")
    
    g = Github(credentials.token)
    user = g.get_user()
    open_issues = user.get_user_issues(state='open')
    for issue in open_issues:
        _issue = Issue.objects.filter(github_number=issue.number).first()
        if _issue is not None:
            continue #jump to the next issue

        p = re.compile("<hrs>(\d)</hrs>")
        result = p.search(issue.body)
        hours = 0
        if result is not None:
            hours = float(result.group(1))

        new_issue = Issue(
            title=issue.title,
            github_number=issue.number,
            body=issue.body[0:500],
            url=issue.url,
            freelancer=freelancer,
            duration_in_minutes=hours * 60,
            duration_in_hours=hours,
        )
        new_issue.save()

    return None

def change_status(issue, status):
    issue.status = status
    issue.save()
    return None

def generate_freelancer_bill(reviewer, freelancer):

    open_bill = Bill.objects.filter(freelancer__id=freelancer.id, status='DUE').first()
    if open_bill is None:
        open_bill = Bill(
            reviewer=reviewer,
            freelancer=freelancer,
        )
        open_bill.save()
    
    done_issues = Issue.objects.filter(status='DONE', bill__isnull=True)
    total = { 
        "minutes": open_bill.total_duration_in_minutes, 
        "hours": open_bill.total_duration_in_hours, 
        "price": open_bill.total_price 
    }
    print(f"{done_issues.count()} issues found")
    for issue in done_issues:
        issue.bill = open_bill
        issue.save()
        total["hours"] = total["hours"] + issue.duration_in_hours
        total["minutes"] = total["minutes"] + issue.duration_in_minutes
    total["price"] = total["hours"] * freelancer.price_per_hour

    open_bill.total_duration_in_hours = total["hours"]
    open_bill.total_duration_in_minutes = total["minutes"]
    open_bill.total_price = total["price"]
    open_bill.save()

    return None