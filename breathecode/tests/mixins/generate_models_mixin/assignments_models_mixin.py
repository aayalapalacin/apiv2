"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models


class AssignmentsModelsMixin(ModelsMixin):
    def generate_assignments_models(self,
                                    task=False,
                                    task_status='',
                                    task_type='',
                                    task_revision_status='',
                                    models={},
                                    task_kwargs={},
                                    **kwargs):
        models = models.copy()

        if not 'task' in models and is_valid(task):
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            if task_status:
                kargs['task_status'] = task_status

            if task_type:
                kargs['task_type'] = task_type

            if task_revision_status:
                kargs['revision_status'] = task_revision_status

            models['task'] = create_models(task, 'assignments.Task', **{**kargs, **task_kwargs})

        return models
