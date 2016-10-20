# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from .models import Workflow, State, Transition, EventType, Event


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """
    Workflow administration
    """
    list_display = ['name', 'description', 'status', 'created_on', 'created_by', 'cloned_from']
    search_fields = ['name', 'description']
    save_on_top = True
    exclude = ['created_on', 'cloned_from']
    list_filter = ['status']


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    """
    State administration
    """
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    save_on_top = True


@admin.register(Transition)
class TransitionAdmin(admin.ModelAdmin):
    """
    Transition administation
    """
    list_display = ['name', 'from_state', 'to_state']
    search_fields = ['name']
    save_on_top = True


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    """
    EventType administration
    """
    list_display = ['name', 'description']
    save_on_top = True
    search_fields = ['name', 'description']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """
    Event administration
    """
    list_display = ['name', 'description', 'workflow', 'state', 'is_mandatory']
    save_on_top = True
    search_fields = ['name', 'description']
    list_filter = ['event_types', 'is_mandatory']
