# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Workflow, State, Transition, WorkflowActivity, WorkflowHistory


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'status', 'created_by', 'created_on']
    search_fields = ['name', 'description']
    save_on_top = True
    list_filter = ['status']


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    save_on_top = True


@admin.register(Transition)
class TransitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'from_state', 'to_state']
    search_fields = ['name', 'description']
    save_on_top = True


@admin.register(WorkflowActivity)
class WorkflowActivityAdmin(admin.ModelAdmin):
    list_display = ['id', 'workflow']
    save_on_top = True
    search_fields = ['id']


@admin.register(WorkflowHistory)
class WorkflowHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'workflowactivity', 'log_type', 'state', 'transition', 'note', 'deadline', 'created_by', 'created_on'
    ]
    save_on_top = True
    search_fields = ['id']
    list_filter = ['id', 'log_type']
