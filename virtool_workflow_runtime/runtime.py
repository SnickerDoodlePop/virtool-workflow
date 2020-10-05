from virtool_workflow import Workflow
import virtool_workflow.execute
from .job import Job
from .db import set_database_updates, DATABASE_NAME


async def execute(workflow: Workflow, job_id: str, database_name: str = DATABASE_NAME):
    job = Job(job_id, workflow)
    set_database_updates(job, database_name=database_name)
    return await virtool_workflow.execute.execute(job.workflow, context=job.context)

