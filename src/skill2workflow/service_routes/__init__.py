"""HTTP routing inventory shared by the service dispatcher.

Path parsers keep the existing identifier/decoding contract. Regex entries
only select candidate routes; malformed parameters retain webhook fallback.
"""

import re

from .workflows import WorkflowRoutes
from .runs import RunRoutes
from .schedules import ScheduleRoutes
from .backup import BackupRoutes
from .ops import OpsRoutes

__all__ = ["WorkflowRoutes", "RunRoutes", "ScheduleRoutes", "BackupRoutes", "OpsRoutes", "dispatch", "EXACT_ROUTES", "PARAMETER_ROUTES"]

EXACT_ROUTES = {('GET', '/healthz'): ('_handle_health', ()),
 ('GET', '/readyz'): ('_handle_ready', ()),
 ('GET', '/metrics'): ('_handle_metrics', ()),
 ('GET', '/api/v1/control-snapshot'): ('_handle_control_snapshot', ()),
 ('GET', '/api/v1/workflow-artifacts'): ('_handle_workflow_artifact_report', ()),
 ('GET', '/api/v1/backup-readiness'): ('_handle_backup_readiness', ()),
 ('GET', '/api/v1/backup-inventory'): ('_handle_backup_inventory', ()),
 ('GET', '/api/v1/backup-inventory-pages'): ('_handle_backup_inventory_page', ()),
 ('POST', '/api/v1/backup-retention-plan'): ('_handle_backup_retention_plan', ()),
 ('POST', '/api/v1/retention-readiness'): ('_handle_retention_readiness', ()),
 ('GET', '/api/v1/operational-readiness'): ('_handle_operational_readiness', ()),
 ('GET', '/api/v1/audit-integrity'): ('_handle_audit_integrity', ()),
 ('GET', '/api/v1/runtime-info'): ('_handle_runtime_info', ()),
 ('GET', '/api/v1/workflows'): ('_handle_workflow_inventory', ()),
 ('POST', '/api/v1/workflow-release-preflights'): ('_handle_workflow_release_preflight', ()),
 ('POST', '/api/v1/workflow-release-target-reviews'): ('_handle_workflow_release_target_review',
                                                       ()),
 ('POST', '/api/v1/workflow-releases'): ('_handle_workflow_release', ()),
 ('POST', '/api/v1/workflow-promotions'): ('_handle_workflow_promotion', ()),
 ('POST', '/api/v1/workflow-deprecations'): ('_handle_workflow_deprecation', ()),
 ('GET', '/api/v1/recurring-schedules'): ('_handle_recurring_schedule_list', ()),
 ('POST', '/api/v1/recurring-schedules'): ('_handle_recurring_schedule_create', ()),
 ('GET', '/api/v1/audit-consistency'): ('_handle_audit_consistency', ('',)),
 ('GET', '/api/v1/support-bundle'): ('_handle_support_bundle', ()),
 ('GET', '/runs'): ('_handle_run_list', ()),
 ('GET', '/api/v1/runs'): ('_handle_run_page', ()),
 ('GET', '/api/v1/audit-events'): ('_handle_audit_event_page', ())}

# Ordered as in the original dispatcher. The boolean preserves each parser's
# distinction between an empty valid selector and an invalid selector.
PARAMETER_ROUTES = [
    (('GET',), re.compile('/api/v1/workflow-explanations/[^/]*/[^/]*'), '_workflow_explanation_parts', '_handle_workflow_explanation', True, 'normal'),
    (('POST',), re.compile('/api/v1/workflow-preflights/[^/]*/[^/]*'), '_workflow_preflight_parts', '_handle_workflow_preflight', True, 'normal'),
    (('GET',), re.compile('/api/v1/workflow-diffs/[^/]*/[^/]*/[^/]*'), '_workflow_diff_parts', '_handle_workflow_diff', True, 'normal'),
    (('PATCH',), re.compile('/api/v1/recurring-schedules/[^/]*'), '_recurring_schedule_patch', '_handle_recurring_schedule_patch', False, 'normal'),
    (('PUT',), re.compile('/api/v1/recurring-schedules/[^/]*'), '_recurring_schedule_update', '_handle_recurring_schedule_update', False, 'normal'),
    (('DELETE',), re.compile('/api/v1/recurring-schedules/[^/]*'), '_recurring_schedule_delete', '_handle_recurring_schedule_delete', False, 'normal'),
    (('POST',), re.compile('/api/v1/recurring-schedules/[^/]*/(?:enable|disable)'), '_recurring_schedule_action', '_handle_recurring_schedule_action', False, 'action'),
    (('GET', 'POST'), re.compile('/api/v1/recurring-schedule-dispatches/[^/]*/review'), '_recurring_schedule_dispatch_review', '_handle_recurring_schedule_dispatch_review', False, 'review'),
    (('GET',), re.compile('/api/v1/(?:recurring-schedule-dispatches|recurring-schedules/[^/]*/dispatches)'), '_recurring_schedule_dispatch_list', '_handle_recurring_schedule_dispatch_list', True, 'normal'),
    (('GET',), re.compile('/api/v1/(?:recurring-schedule-dispatch-pages|recurring-schedules/[^/]*/dispatch-pages)'), '_recurring_schedule_dispatch_page', '_handle_recurring_schedule_dispatch_page', True, 'normal'),
    (('GET',), re.compile('/api/v1/audit-consistency/[^/]*'), '_audit_consistency_run_id', '_handle_audit_consistency', False, 'normal'),
    (('GET',), re.compile('/runs/[^/]*'), '_run_detail_id', '_handle_run_detail', False, 'normal'),
    (('POST',), re.compile('/runs/[^/]*/resume'), '_resume_run_id', '_handle_resume', False, 'normal'),
    (('POST',), re.compile('/runs/[^/]*/cancel'), '_cancel_run_id', '_handle_cancel', False, 'normal'),
]


def dispatch(handler, method, path):
    from .. import service as service_module

    exact = EXACT_ROUTES.get((method, path))
    if exact is not None:
        name, arguments = exact
        return getattr(handler, name)(*arguments)
    for methods, pattern, parser_name, name, accepts_empty, mode in PARAMETER_ROUTES:
        if method not in methods or pattern.fullmatch(path) is None:
            continue
        parts = getattr(service_module, parser_name)(path)
        if (accepts_empty and parts is None) or (not accepts_empty and not parts):
            continue
        target = getattr(handler, name)
        if mode == "action":
            schedule_id, action = parts
            return target(schedule_id, enabled=action == "enable")
        if mode == "review":
            return target(parts, write=method == "POST")
        return target(parts)
    return handler._handle_webhook()
