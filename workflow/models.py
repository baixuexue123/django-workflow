# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _, ugettext as __
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from workflow.signals import (
    workflow_started, workflow_pre_change, workflow_post_change,
    workflow_transitioned, workflow_commented, workflow_ended
)
from workflow.exceptions import (
    UnableToActivateWorkflow, UnableToStartWorkflow, UnableToProgressWorkflow,
    UnableToAddCommentToWorkflow,
)


class Workflow(models.Model):
    """
    Instances of this class represent a named workflow that achieve a particular
    aim through a series of related states / transitions. A name for a directed
    graph.
    """
    DEFINITION = 0
    ACTIVE = 1
    RETIRED = 2

    STATUS_CHOICE = (
        (DEFINITION, _('In definition')),
        (ACTIVE, _('Active')),
        (RETIRED, _('Retired')),
    )

    name = models.CharField(_('Workflow Name'), max_length=128)
    label = models.CharField(_('Workflow label'), max_length=64)
    slug = models.SlugField(_('Slug'))
    description = models.TextField(_('Description'), blank=True, default='')
    status = models.IntegerField(_('Status'), choices=STATUS_CHOICE, default=DEFINITION)
    created_by = models.ForeignKey(User)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['status', 'name']
        verbose_name = _('Workflow')
        verbose_name_plural = _('Workflows')
        permissions = (
            ('can_manage_workflows', __('Can manage workflows')),
        )

    def is_valid(self):
        """
        Checks that the directed graph doesn't contain any orphaned nodes (is
        connected), any cul-de-sac nodes (non-end nodes with no exit
        transition), has compatible roles for transitions and states and
        contains exactly one start node and at least one end state.

        Any errors are logged in the errors dictionary.

        Returns a boolean
        """
        self.errors = {
            'workflow': [],
            'states': {},
            'transitions': {},
        }
        valid = True

        # The graph must have only one start node
        if self.states.filter(is_start_state=True).count() != 1:
            self.errors['workflow'].append(__('There must be only one start state'))
            valid = False

        # The graph must have at least one end state
        if self.states.filter(is_end_state=True).count() < 1:
            self.errors['workflow'].append(__('There must be at least one end state'))
            valid = False

        # Check for orphan nodes / cul-de-sac nodes
        all_states = self.states.all()
        for state in all_states:
            if state.transitions_into.all().count() == 0 and not state.is_start_state:
                if state.id not in self.errors['states']:
                    self.errors['states'][state.id] = list()
                self.errors['states'][state.id].append(
                    __('This state is orphaned. '
                       'There is no way to get to it given the current workflow topology.')
                )
                valid = False

            if state.transitions_from.all().count() == 0 and not state.is_end_state:
                if state.id not in self.errors['states']:
                    self.errors['states'][state.id] = list()
                self.errors['states'][state.id].append(
                    __('This state is a dead end. '
                       'It is not marked as an end state and there is no way to exit from it.')
                )
                valid = False

        return valid

    def has_errors(self, thing):
        """
        Utility method to quickly get a list of errors associated with the
        "thing" passed to it (either a state or transition)
        """
        if isinstance(thing, State):
            if thing.id in self.errors['states']:
                return self.errors['states'][thing.id]
            else:
                return []
        elif isinstance(thing, Transition):
            if thing.id in self.errors['transitions']:
                return self.errors['transitions'][thing.id]
            else:
                return []
        else:
            return []

    def activate(self):
        """
        Puts the workflow in the "active" state after checking the directed
        graph doesn't contain any orphaned nodes (is connected), is in 
        DEFINITION state, has compatible roles for transitions and states and
        contains exactly one start state and at least one end state
        """
        # Only workflows in definition state can be activated
        if self.status != self.DEFINITION:
            raise UnableToActivateWorkflow(
                __('Only workflows in the "definition" state may be activated')
            )
        if not self.is_valid():
            raise UnableToActivateWorkflow(
                __("Cannot activate as the workflow doesn't validate.")
            )

        self.status = self.ACTIVE
        self.save()

    def retire(self):
        """
        Retires the workflow so it can no-longer be used with new
        WorkflowActivity models
        """
        self.status = self.RETIRED
        self.save()

    def __unicode__(self):
        return self.name


class State(models.Model):
    """
    Represents a specific state that a thing can be in during its progress
    through a workflow. A node in a directed graph.
    """

    # Constant values to denote a period of time in seconds
    SECOND = 1
    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    WEEK = 604800

    DURATIONS = (
        (SECOND, _('Second(s)')),
        (MINUTE, _('Minute(s)')),
        (HOUR, _('Hour(s)')),
        (DAY, _('Day(s)')),
        (WEEK, _('Week(s)')),
    )

    name = models.CharField(_('Name'), max_length=256)
    description = models.TextField(_('Description'), blank=True, default='')
    is_start_state = models.BooleanField(_('Is the start state?'), default=False)
    is_end_state = models.BooleanField(_('Is an end state?'), default=False)
    workflow = models.ForeignKey(Workflow, related_name='states')
    # The users and groups defined here define *who* has permission to
    # view the item in this state.
    users = models.ManyToManyField(User, blank=True)
    groups = models.ManyToManyField(Group, blank=True)
    # 下面两个字段指定这个状态的过期时间
    # TODO models.DurationField
    estimation_value = models.IntegerField(
            _('Estimated time (value)'), default=0,
            help_text=_('Use whole numbers')
        )
    estimation_unit = models.IntegerField(
            _('Estimation unit of time'), default=DAY, choices=DURATIONS
        )

    class Meta:
        ordering = ['-is_start_state', 'is_end_state']
        verbose_name = _('State')
        verbose_name_plural = _('States')

    def deadline(self):
        """
        Will return the expected deadline (or None) for this state calculated
        from datetime.today()
        """
        if self.estimation_value > 0:
            duration = datetime.timedelta(seconds=(self.estimation_value * self.estimation_unit))
            return datetime.datetime.today() + duration
        else:
            return None

    def __unicode__(self):
        return self.name


class Transition(models.Model):
    """
    Represents how a workflow can move between different states. An edge
    between state "nodes" in a directed graph.
    """
    name = models.CharField(_('Name of transition'), max_length=128)
    description = models.TextField(_('Description'), blank=True, default='')
    workflow = models.ForeignKey(Workflow, related_name='transitions')
    from_state = models.ForeignKey(State, related_name='transitions_from')
    to_state = models.ForeignKey(State, related_name='transitions_into')
    # The users and groups referenced here define *who* has permission to
    # use this transition to move between states.
    users = models.ManyToManyField(User, blank=True)
    groups = models.ManyToManyField(Group, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('Transition')
        verbose_name_plural = _('Transitions')


class WorkflowActivity(models.Model):
    """
    Other models in a project reference this model so they become associated
    with a particular workflow.

    The WorkflowActivity object also contains *all* the methods required to
    start, progress and stop a workflow.
    """
    workflow = models.ForeignKey(Workflow)
    created_by = models.ForeignKey(User)
    created_on = models.DateTimeField(auto_now_add=True)
    completed_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_on', '-completed_on']
        verbose_name = _('Workflow Activity')
        verbose_name_plural = _('Workflow Activities')
        permissions = (
            ('can_start_workflow', __('Can start a workflow')),
            ('can_assign_roles', __('Can assign roles'))
        )

    def current_state(self):
        """
        Returns the instance of the WorkflowHistory model that represents the 
        current state this WorkflowActivity is in.
        """
        if self.history.all():
            return self.history.all().first()
        else:
            return None

    def start(self, user):
        """
        Starts a WorkflowActivity by putting it into the start state of the
        workflow defined in the "workflow" field after validating the workflow
        activity is in a state appropriate for "starting"
        """
        start_state_result = State.objects.filter(workflow=self.workflow, is_start_state=True)
        # Validation
        # 1. The workflow activity isn't already started
        if self.current_state():
            if self.current_state().state:
                raise UnableToStartWorkflow(__('Already started'))
        # 2. The workflow activity hasn't been force_stopped before being started
        if self.completed_on:
            raise UnableToStartWorkflow(__('Already completed'))
        # 3. There is exactly one start state
        if start_state_result.count() != 1:
            raise UnableToStartWorkflow(__('Cannot find single start state'))

        first_step = WorkflowHistory(
                workflowactivity=self,
                state=start_state_result.first(),
                log_type=WorkflowHistory.TRANSITION,
                note=__('Started workflow'),
                created_by=user,
                deadline=start_state_result.first().deadline()
            )
        first_step.save()
        return first_step

    def progress(self, transition, user, note=''):
        """
        Attempts to progress a workflow activity with the specified transition

        The transition is validated (to make sure it is a legal "move" in the
        directed graph) and the method returns the new WorkflowHistory state or
        raises an UnableToProgressWorkflow exception.
        """
        # Validate the transition
        current_state = self.current_state()
        # 1. Make sure the workflow activity is started
        if not current_state:
            raise UnableToProgressWorkflow(__('Start the workflow before attempting to transition'))
        # 2. Make sure it's parent is the current state
        if transition.from_state != current_state.state:
            raise UnableToProgressWorkflow(__('Transition not valid (wrong parent)'))

        # The "progress" request has been validated to store the transition into
        # the appropriate WorkflowHistory record and if it is an end state then
        # update this WorkflowActivity's record with the appropriate timestamp
        wh = WorkflowHistory(
                workflowactivity=self,
                state=transition.to_state,
                log_type=WorkflowHistory.TRANSITION,
                transition=transition,
                note=note if note else transition.name,
                created_by=user,
                deadline=transition.to_state.deadline()
            )
        wh.save()
        # If we're at the end then mark the workflow activity as completed on today
        if transition.to_state.is_end_state:
            self.completed_on = datetime.datetime.today()
            self.save()
        return wh

    def add_comment(self, user, note):
        """
        In many sorts of workflow it is necessary to add a comment about
        something at a particular state in a WorkflowActivity.
        """
        if not note:
            raise UnableToAddCommentToWorkflow(__('Cannot add an empty comment(note)'))
        current_state = self.current_state().state if self.current_state() else None
        deadline = self.current_state().deadline if current_state else None
        wh = WorkflowHistory(
                workflowactivity=self,
                state=current_state,
                log_type=WorkflowHistory.COMMENT,
                note=note,
                created_by=user,
                deadline=deadline
            )
        wh.save()
        return wh

    def force_stop(self, user, reason):
        """
        Should a WorkflowActivity need to be abandoned this method cleanly logs
        the event and puts the WorkflowActivity in the appropriate state (with
        reason provided by participant).
        """
        # Lets try to create an appropriate entry in the WorkflowHistory table
        current_state = self.current_state()
        if current_state:
            final_step = WorkflowHistory(
                    workflowactivity=self,
                    state=current_state.state,
                    log_type=WorkflowHistory.TRANSITION,
                    note=__('Workflow forced to stop! Reason given: %s') % reason,
                    created_by=user,
                    deadline=None
                )
            final_step.save()

        self.completed_on = datetime.datetime.today()
        self.save()


class WorkflowHistory(models.Model):
    """
    Records what has happened and when in a particular run of a workflow. The
    latest record for the referenced WorkflowActivity will indicate the current 
    state.
    """

    # The sort of things we can log in the workflow history
    TRANSITION = 1
    COMMENT = 2

    LOG_TYPE_CHOICE = (
        (TRANSITION, _('Transition')),
        (COMMENT, _('Comment')),
    )

    workflowactivity = models.ForeignKey(WorkflowActivity, related_name='history')
    log_type = models.IntegerField(
            choices=LOG_TYPE_CHOICE,
            help_text=_('The sort of thing being logged')
        )
    state = models.ForeignKey(
            State, null=True,
            help_text=_('The state at this point in the workflow history')
        )
    transition = models.ForeignKey(
            Transition, null=True, related_name='history',
            help_text=_('The transition relating to this happening in the workflow history')
        )
    note = models.TextField(_('Note'), blank=True, default='')
    created_by = models.ForeignKey(User)
    created_on = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(
            _('Deadline'), blank=True, null=True,
            help_text=_('The deadline for staying in this state')
        )

    class Meta:
        ordering = ['-created_on']
        verbose_name = _('Workflow History')
        verbose_name_plural = _('Workflow Histories')

    def save(self, *args, **kwargs):
        workflow_pre_change.send(sender=self)
        super(WorkflowHistory, self).save(*args, **kwargs)
        workflow_post_change.send(sender=self)
        if self.log_type == self.TRANSITION:
            workflow_transitioned.send(sender=self)
        elif self.log_type == self.COMMENT:
            workflow_commented.send(sender=self)
        if self.state:
            if self.state.is_start_state:
                workflow_started.send(sender=self.workflowactivity)
            elif self.state.is_end_state:
                workflow_ended.send(sender=self.workflowactivity)

    def __unicode__(self):
        return '%s created by %s' % (self.note, self.user.get_full_name())


class WorkflowObjectRelation(models.Model):
    """Stores an workflow of an object.
    Provides a way to give any object a workflow without changing the object's
    model.
    **Attributes:**
    content
        The object for which the workflow is stored. This can be any instance of
        a Django model.
    workflow
        The workflow which is assigned to an object. This needs to be a workflow
        instance.
    """

    content_type = models.ForeignKey(ContentType, related_name='workflow_object')
    content_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey(ct_field='content_type', fk_field='content_id')
    workflow = models.ForeignKey(Workflow, verbose_name=_('Workflow'))

    class Meta:
        unique_together = ('content_type', 'content_id')
        verbose_name = _('Workflow object relation')
        verbose_name_plural = _('Workflow object relations')

    def __unicode__(self):
        return '%s %s - %s' % (self.content_type, self.content_id, self.workflow.name)


class WorkflowModelRelation(models.Model):
    """Stores an workflow for a model (ContentType).
    Provides a way to give any object a workflow without changing the model.
    **Attributes:**
    Content Type
        The content type for which the workflow is stored. This can be any
        instance of a Django model.
    workflow
        The workflow which is assigned to an object. This needs to be a
        workflow instance.
    """

    class Meta:
        verbose_name = _('Workflow model relation')
        verbose_name_plural = _('Workflow model relations')

    content_type = models.ForeignKey(ContentType, verbose_name=_('Content Type'))
    workflow = models.ForeignKey(Workflow, verbose_name=_('Workflow'))

    def __unicode__(self):
        return '%s - %s' % (self.content_type.name, self.workflow.name)
