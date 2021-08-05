#!/usr/bin/env python
"""
Alert me when something is missing with the Slack integration
"""
from breathecode.notify.models import SlackTeam
from breathecode.authenticate.models import CredentialsSlack
from django.db.models import Q
from breathecode.services.slack import client
from breathecode.utils import ScriptNotification

slack = SlackTeam.objects.filter(academy__id=academy.id).first()
if slack is None:
    raise ScriptNotification(title='No slack integration has been found',
                             status='MINOR')

owner_credentials = CredentialsSlack.objects.filter(
    user__id=slack.owner.id).first()
if owner_credentials is None:
    raise ScriptNotification(
        title='The academy slack integration is not finished, the team owner needs to connect with slack',
        status='MINOR')

api = client.Slack(token)
data = api.post('api.test')
print("data", data)