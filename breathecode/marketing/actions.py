import os, re, requests
from typing import Optional
from itertools import chain
from django.utils import timezone

from breathecode.utils.i18n import translation
from .models import FormEntry, Tag, Automation, ActiveCampaignAcademy, AcademyAlias
from rest_framework.exceptions import APIException
from breathecode.notify.actions import send_email_message
from breathecode.authenticate.models import CredentialsFacebook
from breathecode.services.activecampaign import AC_Old_Client, ActiveCampaign, ActiveCampaignClient
from breathecode.utils.validation_exception import ValidationException
from breathecode.marketing.models import Tag
from breathecode.utils import getLogger
import numpy as np

logger = getLogger(__name__)

GOOGLE_CLOUD_KEY = os.getenv('GOOGLE_CLOUD_KEY')


def get_save_leads():
    return os.getenv('SAVE_LEADS')


acp_ids = {
    # "strong": "49",
    # "soft": "48",
    # "newsletter_list": "3",
    'utm_plan': '67',
    'utm_placement': '66',
    'utm_term': '65',
    'utm_source': '59',
    'utm_medium': '36',
    'utm_content': '35',
    'utm_url': '60',
    'utm_location': '18',
    'utm_campaign': '33',
    'gender': '45',
    'course': '2',
    'client_comments': '13',
    'current_download': '46',  # used in downloadables
    'utm_language': '16',
    'utm_country': '19',
    'gclid': '26',
    'referral_key': '27',
    'deal': {
        'expected_cohort': '10',
        'expected_cohort_date': '21',
        'utm_location': '16',
        'utm_course': '6',
    }
}


def set_optional(contact, key, data, custom_key=None):
    if custom_key is None:
        custom_key = key

    if custom_key in data:
        contact['field[' + acp_ids[key] + ',0]'] = data[custom_key]

    return contact


def get_lead_tags(ac_academy, form_entry):
    if 'tags' not in form_entry or form_entry['tags'] == '':
        raise Exception('You need to specify tags for this entry')
    else:
        _tags = [t.strip() for t in form_entry['tags'].split(',')]
        if len(_tags) == 0 or _tags[0] == '':
            raise Exception('The contact tags are empty', 400)

    strong_tags = Tag.objects.filter(slug__in=_tags, tag_type='STRONG', ac_academy=ac_academy)
    soft_tags = Tag.objects.filter(slug__in=_tags, tag_type='SOFT', ac_academy=ac_academy)
    dicovery_tags = Tag.objects.filter(slug__in=_tags, tag_type='DISCOVERY', ac_academy=ac_academy)
    other_tags = Tag.objects.filter(slug__in=_tags, tag_type='OTHER', ac_academy=ac_academy)

    tags = list(chain(strong_tags, soft_tags, dicovery_tags, other_tags))
    if len(tags) != len(_tags):
        message = 'Some tag applied to the contact not found or have tag_type different than [STRONG, SOFT, DISCOVER, OTHER]: '
        message += f'Check for the follow tags:  {",".join(_tags)}'
        raise Exception(message)

    return tags


def get_lead_automations(ac_academy, form_entry):
    _automations = []
    if 'automations' not in form_entry or form_entry['automations'] == '':
        return []
    else:
        _automations = form_entry['automations'].split(',')

    automations = Automation.objects.filter(slug__in=_automations, ac_academy=ac_academy)
    count = automations.count()
    if count == 0:
        _name = form_entry['automations']
        raise Exception(f'The specified automation {_name} was not found for this AC Academy')

    logger.debug(f'found {str(count)} automations')
    return automations.values_list('acp_id', flat=True)


def add_to_active_campaign(contact, academy_id: int, automation_id: int):
    if not ActiveCampaignAcademy.objects.filter(academy__id=academy_id).count():
        raise Exception(f'No academy found with id {academy_id}')

    active_campaign_academy_values = ['ac_url', 'ac_key', 'event_attendancy_automation__id']
    ac_url, ac_key, event_attendancy_automation_id = ActiveCampaignAcademy.objects.filter(
        academy__id=academy_id).values_list(*active_campaign_academy_values).first()

    logger.info('ready to send contact with following details')
    logger.info(contact)

    old_client = AC_Old_Client(ac_url, ac_key)
    response = old_client.contacts.create_contact(contact)
    contact_id = response['subscriber_id']

    if 'subscriber_id' not in response:
        logger.error('error adding contact', response)
        raise APIException('Could not save contact in CRM')

    client = ActiveCampaignClient(ac_url, ac_key)

    if event_attendancy_automation_id != automation_id:
        message = 'Automation doesn\'t exist for this AC Academy'
        logger.info(message)
        raise Exception(message)

    acp_id = Automation.objects.filter(id=automation_id).values_list('acp_id', flat=True).first()

    if not acp_id:
        message = 'Automation acp_id doesn\'t exist'
        logger.info(message)
        raise Exception(message)

    data = {
        'contactAutomation': {
            'contact': contact_id,
            'automation': acp_id,
        }
    }

    response = client.contacts.add_a_contact_to_an_automation(data)

    if 'contacts' not in response:
        logger.error(f'error triggering automation with id {str(acp_id)}', response)
        raise APIException('Could not add contact to Automation')

    logger.info(f'Triggered automation with id {str(acp_id)}', response)


def register_new_lead(form_entry=None):
    if form_entry is None:
        raise ValidationException('You need to specify the form entry data')

    if 'location' not in form_entry or form_entry['location'] is None:
        raise ValidationException('Missing location information')

    ac_academy = None
    alias = AcademyAlias.objects.filter(active_campaign_slug=form_entry['location']).first()

    try:
        if alias is not None:
            ac_academy = alias.academy.activecampaignacademy
    except:
        pass

    if ac_academy is None:
        ac_academy = ActiveCampaignAcademy.objects.filter(academy__slug=form_entry['location']).first()

    if ac_academy is None:
        raise ValidationException(f"No academy found with slug {form_entry['location']}")

    automations = get_lead_automations(ac_academy, form_entry)

    if automations:
        logger.info('found automations')
        logger.info(list(automations))
    else:
        logger.info('automations not found')

    tags = get_lead_tags(ac_academy, form_entry)
    logger.info('found tags')
    logger.info(set(t.slug for t in tags))

    if (automations is None or len(automations) == 0) and len(tags) > 0:
        if tags[0].automation is None:
            raise ValidationException(
                'No automation was specified and the the specified tag has no automation either')

        automations = [tags[0].automation.acp_id]

    if not 'email' in form_entry:
        raise ValidationException('The email doesn\'t exist')

    if not 'first_name' in form_entry:
        raise ValidationException('The first name doesn\'t exist')

    if not 'last_name' in form_entry:
        raise ValidationException('The last name doesn\'t exist')

    if not 'phone' in form_entry:
        raise ValidationException('The phone doesn\'t exist')

    if not 'id' in form_entry:
        raise ValidationException('The id doesn\'t exist')

    if not 'course' in form_entry:
        raise ValidationException('The course doesn\'t exist')

    # apply default language and make sure english is "en" and not "us"
    if 'utm_language' in form_entry and form_entry['utm_language'] == 'us':
        form_entry['utm_language'] = 'en'
    elif 'language' in form_entry and form_entry['language'] == 'us':
        form_entry['language'] = 'en'

    contact = {
        'email': form_entry['email'],
        'first_name': form_entry['first_name'],
        'last_name': form_entry['last_name'],
        'phone': form_entry['phone']
    }

    contact = set_optional(contact, 'utm_url', form_entry)
    contact = set_optional(contact, 'utm_location', form_entry, 'location')
    contact = set_optional(contact, 'course', form_entry)
    contact = set_optional(contact, 'utm_language', form_entry, 'language')
    contact = set_optional(contact, 'utm_country', form_entry, 'country')
    contact = set_optional(contact, 'utm_campaign', form_entry)
    contact = set_optional(contact, 'utm_source', form_entry)
    contact = set_optional(contact, 'utm_content', form_entry)
    contact = set_optional(contact, 'utm_medium', form_entry)
    contact = set_optional(contact, 'utm_plan', form_entry)
    contact = set_optional(contact, 'utm_placement', form_entry)
    contact = set_optional(contact, 'utm_term', form_entry)
    contact = set_optional(contact, 'gender', form_entry, 'sex')
    contact = set_optional(contact, 'client_comments', form_entry)
    contact = set_optional(contact, 'gclid', form_entry)
    contact = set_optional(contact, 'current_download', form_entry)
    contact = set_optional(contact, 'referral_key', form_entry)

    entry = FormEntry.objects.filter(id=form_entry['id']).first()

    if not entry:
        raise ValidationException('FormEntry not found (id: ' + str(form_entry['id']) + ')')

    if 'contact-us' == tags[0].slug:
        send_email_message(
            'new_contact',
            ac_academy.academy.marketing_email,
            {
                'subject':
                f"New contact from the website {form_entry['first_name']} {form_entry['last_name']}",
                'full_name': form_entry['first_name'] + ' ' + form_entry['last_name'],
                'client_comments': form_entry['client_comments'],
                'data': {
                    **form_entry
                },
                # "data": { **form_entry, **address },
            })

    is_duplicate = entry.is_duplicate(form_entry)
    # ENV Variable to fake lead storage

    if get_save_leads() == 'FALSE':
        entry.storage_status_text = 'Saved but not send to AC because SAVE_LEADS is FALSE'
        entry.storage_status = 'PERSISTED' if not is_duplicate else 'DUPLICATED'
        entry.save()
        return entry

    logger.info('ready to send contact with following details: ' + str(contact))
    old_client = AC_Old_Client(ac_academy.ac_url, ac_academy.ac_key)
    response = old_client.contacts.create_contact(contact)
    contact_id = response['subscriber_id']

    # save contact_id from active campaign
    entry.ac_contact_id = contact_id
    entry.save()

    if 'subscriber_id' not in response:
        logger.error('error adding contact', response)
        entry.storage_status = 'ERROR'
        entry.storage_status_text = 'Could not save contact in CRM: Subscriber_id not found'
        entry.save()

    if is_duplicate:
        entry.storage_status = 'DUPLICATED'
        entry.save()
        logger.info('FormEntry is considered a duplicate, no automations or tags added')
        return entry

    client = ActiveCampaignClient(ac_academy.ac_url, ac_academy.ac_key)
    if automations and not is_duplicate:
        for automation_id in automations:
            data = {'contactAutomation': {'contact': contact_id, 'automation': automation_id}}
            response = client.contacts.add_a_contact_to_an_automation(data)

            if 'contacts' not in response:
                logger.error(f'error triggering automation with id {str(automation_id)}', response)
                raise APIException('Could not add contact to Automation')
            logger.info(f'Triggered automation with id {str(automation_id)} ' + str(response))

        logger.info('automations was executed successfully')

    if tags and not is_duplicate:
        for t in tags:
            data = {'contactTag': {'contact': contact_id, 'tag': t.acp_id}}
            response = client.contacts.add_a_tag_to_contact(data)
        logger.info('contact was tagged successfully')

    entry.storage_status = 'PERSISTED'
    entry.save()

    form_entry['storage_status'] = 'PERSISTED'

    return entry


def test_ac_connection(ac_academy):
    client = ActiveCampaignClient(ac_academy.ac_url, ac_academy.ac_key)
    response = client.tags.list_all_tags(limit=1)
    return response


def sync_tags(ac_academy):

    client = ActiveCampaignClient(ac_academy.ac_url, ac_academy.ac_key)
    response = client.tags.list_all_tags(limit=100)

    if 'tags' not in response:
        logger.error('Invalid tags incoming from AC')
        return False

    tags = response['tags']
    count = 0
    while len(response['tags']) == 100:
        count = count + 100
        response = client.tags.list_all_tags(limit=100, offset=count)
        tags = tags + response['tags']

    for tag in tags:
        t = Tag.objects.filter(slug=tag['tag'], ac_academy=ac_academy).first()
        if t is None:
            t = Tag(
                slug=tag['tag'],
                acp_id=tag['id'],
                ac_academy=ac_academy,
            )

        t.subscribers = tag['subscriber_count']
        t.save()

    return response


def sync_automations(ac_academy):

    client = ActiveCampaignClient(ac_academy.ac_url, ac_academy.ac_key)
    response = client.automations.list_all_automations(limit=100)

    if 'automations' not in response:
        logger.error('Invalid automations incoming from AC')
        return False

    automations = response['automations']
    count = 0
    while len(response['automations']) == 100:
        count = count + 100
        response = client.tags.list_all_tags(limit=100, offset=count)
        if 'automations' not in response:
            logger.error('Invalid automations incoming from AC')
            return False
        automations = automations + response['automations']

    for auto in automations:
        a = Automation.objects.filter(acp_id=auto['id'], ac_academy=ac_academy).first()
        if a is None:
            a = Automation(
                acp_id=auto['id'],
                ac_academy=ac_academy,
            )
        a.name = auto['name']
        a.entered = auto['entered']
        a.exited = auto['exited']
        a.status = auto['status']
        a.save()

    return response


def save_get_geolocal(contact, form_entry=None):

    if 'latitude' not in form_entry or 'longitude' not in form_entry:
        form_entry = contact.toFormData()

    if 'latitude' not in form_entry or 'longitude' not in form_entry:
        return False
    if form_entry['latitude'] == '' or form_entry[
            'longitude'] == '' or form_entry['latitude'] is None or form_entry['longitude'] is None:
        return False

    result = {}
    resp = requests.get(
        f"https://maps.googleapis.com/maps/api/geocode/json?latlng={form_entry['latitude']},{form_entry['longitude']}&key={GOOGLE_CLOUD_KEY}",
        timeout=2)
    data = resp.json()
    if 'status' in data and data['status'] == 'INVALID_REQUEST':
        raise Exception(data['error_message'])

    if 'results' in data:
        for address in data['results']:
            for component in address['address_components']:
                if 'country' in component['types'] and 'country' not in result:
                    result['country'] = component['long_name']
                if 'locality' in component['types'] and 'locality' not in result:
                    result['locality'] = component['long_name']
                if 'route' in component['types'] and 'route' not in result:
                    result['route'] = component['long_name']
                if 'postal_code' in component['types'] and 'postal_code' not in result:
                    result['postal_code'] = component['long_name']

    if 'country' in result:
        contact.country = result['country']

    if 'locality' in result:
        contact.city = result['locality']

    if 'route' in result:
        contact.street_address = result['route']

    if 'postal_code' in result:
        contact.zip_code = result['postal_code']

    contact.save()

    return True


def get_facebook_lead_info(lead_id, academy_id=None):

    now = timezone.now()

    lead = FormEntry.objects.filter(lead_id=lead_id).first()
    if lead is None:
        raise APIException(f'Invalid lead id: {lead_id}')

    credential = CredentialsFacebook.objects.filter(academy__id=academy_id, expires_at__gte=now).first()
    if credential is None:
        raise APIException('No active facebook credentials to get the leads')

    params = {'access_token': credential.token}
    resp = requests.get(f'https://graph.facebook.com/v8.0/{lead_id}/', params=params, timeout=2)
    if resp.status_code == 200:
        logger.debug('Facebook responded with 200')
        data = resp.json()
        if 'field_data' in data:
            lead.utm_campaign == data['ad_id']
            lead.utm_medium == data['ad_id']
            lead.utm_source == 'facebook'
            for field in data['field_data']:
                if field['name'] == 'first_name' or field['name'] == 'full_name':
                    lead.first_name == field['values']
                elif field['name'] == 'last_name':
                    lead.last_name == field['values']
                elif field['name'] == 'email':
                    lead.email == field['values']
                elif field['name'] == 'phone':
                    lead.phone == field['values']
            lead.save()
        else:
            logger.fatal('No information about the lead')
    else:
        logger.fatal('Impossible to connect to facebook API and retrieve lead information')


STARTS_WITH_COMMA_PATTERN = re.compile(r'^,')
ENDS_WITH_COMMA_PATTERN = re.compile(r',$')


def validate_marketing_tags(tags: str,
                            academy_id: int,
                            types: Optional[list] = None,
                            lang: str = 'en') -> None:
    if tags.find(',,') != -1:
        raise ValidationException(
            translation(lang,
                        en='You can\'t have two commas together on tags',
                        es='No puedes tener dos comas seguidas en las etiquetas',
                        slug='two-commas-together'))

    if tags.find(' ') != -1:
        raise ValidationException(
            translation(lang,
                        en='Spaces are not allowed on tags',
                        es='No se permiten espacios en los tags',
                        slug='spaces-are-not-allowed'))

    if STARTS_WITH_COMMA_PATTERN.search(tags):
        raise ValidationException(
            translation(lang,
                        en='Tags text cannot start with comma',
                        es='El texto de los tags no puede comenzar con una coma',
                        slug='starts-with-comma'))

    if ENDS_WITH_COMMA_PATTERN.search(tags):
        raise ValidationException(
            translation(lang,
                        en='Tags text cannot ends with comma',
                        es='El texto de los tags no puede terminar con una coma',
                        slug='ends-with-comma'))

    tags = [x for x in tags.split(',') if x]
    if len(tags) < 2:
        raise ValidationException(
            translation(lang,
                        en='Event must have at least two tags',
                        es='El evento debe tener al menos dos tags',
                        slug='have-less-two-tags'))

    _tags = Tag.objects.filter(slug__in=tags, ac_academy__academy__id=academy_id)
    if types:
        _tags = _tags.filter(tag_type__in=types)

    founds = set([x.slug for x in _tags])
    if len(tags) == len(founds):
        return

    not_founds = []
    for tag in tags:
        if tag not in founds:
            not_founds.append(tag)

    if len(types) == 0:
        types = ['ANY']

    raise ValidationException(
        translation(lang,
                    en=f'Following tags not found with types {",".join(types)}: {",".join(not_founds)}',
                    es='Los siguientes tags no se encontraron con los tipos '
                    f'{",".join(types)}: {",".join(not_founds)}',
                    slug='tag-not-exist'))


def delete_tag(tag, include_other_academies=False):

    ac_academy = tag.ac_academy
    if ac_academy is None:
        raise ValidationException(f'Invalid ac_academy for this tag {tag.slug}',
                                  code=400,
                                  slug='invalid-ac_academy')

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
    try:
        if client.delete_tag(tag.id):
            if include_other_academies:
                Tag.objects.filter(slug=tag.slug).delete()
            else:
                tag.delete()

            return True

    except:
        logger.exception(f'There was an error deleting tag for {tag.slug}')
        return False


def convert_data_frame(item):
    if 'Unnamed: 0' in item:
        del item['Unnamed: 0']
    for key in item:
        if isinstance(item[key], np.integer):
            item[key] = int(item[key])
        if isinstance(item[key], np.floating):
            item[key] = float(item[key])
        if isinstance(item[key], np.ndarray):
            item[key] = item[key].tolist()
    return item
