# -*- coding: utf-8 -*-


class UnableToActivateWorkflow(Exception):
    """
    To be raised if unable to activate the workflow because it did not pass the
    validation steps
    """


class UnableToStartWorkflow(Exception):
    """
    To be raised if a WorkflowActivity is unable to start a workflow
    """


class UnableToProgressWorkflow(Exception):
    """
    To be raised if the WorkflowActivity is unable to progress a workflow with a
    particular transition.
    """


class UnableToLogWorkflowEvent(Exception):
    """
    To be raised if the WorkflowActivity is unable to log an event in the
    WorkflowHistory
    """


class UnableToDisableParticipant(Exception):
    """
    To be raised if the WorkflowActivity is unable to disable a participant
    """


class UnableToEnableParticipant(Exception):
    """
    To be raised if the WorkflowActivity is unable to enable a participant
    """
