"""Main entrypoint(s) to the Virtool Workflow Runtime."""
from typing import Dict, Any

from virtool_workflow.execution.hooks import on_update, on_workflow_finish
from virtool_workflow.execution.workflow_executor import WorkflowExecution, WorkflowError
from virtool_workflow.fixtures.scope import WorkflowFixtureScope
from virtool_workflow.workflow import Workflow
from . import hooks
from ._redis import job_id_queue
from .db import VirtoolDatabase


async def execute(job_id: str, workflow: Workflow) -> Dict[str, Any]:
    """
    Execute a workflow as a Virtool Job.

    :param job_id: The id of the job in the Virtool jobs database.
    :param workflow: The workflow to be executed
    :return: A dictionary containing the results from the workflow (the results fixture).
    """

    with WorkflowFixtureScope() as fixtures:
        executor = WorkflowExecution(workflow, fixtures)
        try:
            result = await _execute(job_id, workflow, fixtures, executor)

            await hooks.on_success.trigger(workflow, result)

            return result
        except Exception as e:
            if isinstance(e, WorkflowError):
                await hooks.on_failure.trigger(e)
            else:
                await hooks.on_failure.trigger(WorkflowError(cause=e, context=executor, workflow=workflow))

            raise e


async def _execute(job_id: str,
                   workflow: Workflow,
                   fixtures: WorkflowFixtureScope,
                   executor: WorkflowExecution) -> Dict[str, Any]:

    await hooks.on_load_fixtures.trigger(fixtures)

    database: VirtoolDatabase = await fixtures.instantiate(VirtoolDatabase)

    job_document = await database["jobs"].find_one(dict(_id=job_id))

    executor = WorkflowExecution(workflow, fixtures)

    @on_update(until=on_workflow_finish)
    async def send_database_updates(_, update: str):
        await database.send_update(job_id, executor, update)

    fixtures["job_id"] = job_id
    fixtures["job_document"] = job_document

    return await executor


async def execute_from_redis(workflow: Workflow):
    """Execute jobs from the Redis jobs list."""
    async for job_id in job_id_queue():
        yield await execute(job_id, workflow)
