"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models


class MarketingModelsMixin(ModelsMixin):
    def generate_marketing_models(self,
                                  active_campaign_academy=False,
                                  automation=False,
                                  academy=False,
                                  tag=False,
                                  contact=False,
                                  form_entry=False,
                                  short_link=False,
                                  user=False,
                                  academy_alias=False,
                                  active_campaign_academy_kwargs={},
                                  automation_kwargs={},
                                  tag_kwargs={},
                                  academy_alias_kwargs={},
                                  contact_kwargs={},
                                  form_entry_kwargs={},
                                  short_link_kwargs={},
                                  models={},
                                  **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'active_campaign_academy' in models and is_valid(active_campaign_academy):
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            models['active_campaign_academy'] = create_models(active_campaign_academy,
                                                              'marketing.ActiveCampaignAcademy', **{
                                                                  **kargs,
                                                                  **active_campaign_academy_kwargs
                                                              })

        if not 'automation' in models and is_valid(automation):
            kargs = {}

            if 'active_campaign_academy' in models or active_campaign_academy:
                kargs['ac_academy'] = models['active_campaign_academy']

            models['automation'] = create_models(automation, 'marketing.Automation', **{
                **kargs,
                **automation_kwargs
            })

        if not 'academy_alias' in models and is_valid(academy_alias):
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            models['academy_alias'] = create_models(academy_alias, 'marketing.AcademyAlias', **{
                **kargs,
                **academy_alias_kwargs
            })

        # OneToOneField
        if 'active_campaign_academy' in models and is_valid(active_campaign_academy):
            if 'automation' in models or automation:
                models['active_campaign_academy'].event_attendancy_automation = models['automation']

            models['active_campaign_academy'].save()

        if not 'tag' in models and is_valid(tag):
            kargs = {}

            if 'active_campaign_academy' in models or active_campaign_academy:
                kargs['ac_academy'] = models['active_campaign_academy']

            if 'automation' in models or automation:
                kargs['automation'] = models['automation']

            models['tag'] = create_models(tag, 'marketing.Tag', **{**kargs, **tag_kwargs})

        if not 'contact' in models and is_valid(contact):
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            models['contact'] = create_models(contact, 'marketing.Contact', **{**kargs, **contact_kwargs})

        if not 'form_entry' in models and is_valid(form_entry):
            kargs = {}

            if 'contact' in models or contact:
                kargs['contact'] = models['contact']

            if 'tag' in models or tag:
                kargs['tag_objects'] = [models['tag']]

            if 'automation' in models or automation:
                kargs['automation_objects'] = [models['automation']]

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'active_campaign_academy' in models or active_campaign_academy:
                kargs['ac_academy'] = models['active_campaign_academy']

            models['form_entry'] = create_models(form_entry, 'marketing.FormEntry', **{
                **kargs,
                **form_entry_kwargs
            })

        if not 'short_link' in models and is_valid(short_link):
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'user' in models or user:
                kargs['author'] = models['user']

            models['short_link'] = create_models(short_link, 'marketing.ShortLink', **{
                **kargs,
                **short_link_kwargs
            })

        return models
