import sys
from pathlib import Path

from virtool_workflow_runtime import runtime
from virtool_workflow_runtime.db import VirtoolDatabase
from virtool_workflow_runtime.discovery import discover_workflow

EXAMPLE_WORKFLOW_PATH = Path(sys.path[0]).joinpath("tests/example_workflow.py")


async def test_updates_sent_to_mongo():
    db = VirtoolDatabase("test")
    await db._db.jobs.insert_one({"_id": "1"})
    workflow = discover_workflow(EXAMPLE_WORKFLOW_PATH)

    await runtime.execute(workflow, "1")

    document = await db._db.jobs.find_one({"_id": "1"})

    print(document)

    updates = [status["update"] for status in document["status"]]

    for update in ("Started up", "Step", "Cleaned up"):
        assert update in updates
