import tempfile, unittest
from pathlib import Path
from src.repository import Repository
from src.service import Service
from src.rules import STATES, TRANSITION_ROLES
class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=Repository(str(Path(self.tmp.name)/"test.db")); self.service=Service(self.repo)
    def tearDown(self): self.repo.close(); self.tmp.cleanup()
    def test_complete_workflow_and_audit(self):
        item=self.service.create_item({"title":"workflow item","description":"complete business flow","severity":'exceedance',"quantity":12,"threshold":6,"external_ref":"WF-1"},"creator",'operator')
        self.assertEqual(item["status"],STATES[0])
        record=self.service.add_record(item["id"],{"kind":"remediation","detail":"remediation registered","external_ref":"EV-1"},"recorder",'operator')
        self.assertEqual(record["status"],"pending_review")
        reviewed=self.service.review_record(item["id"],record["id"],{"comment":"rectification verified","expected_version":record["version"]},"officer",'compliance_officer')
        self.assertEqual(reviewed["status"],"closed"); self.assertEqual(reviewed["review_comment"],"rectification verified"); self.assertEqual(reviewed["reviewed_by"],"officer"); self.assertIsNotNone(reviewed["reviewed_at"])
        signoff=self.service.add_record(item["id"],{"kind":"director_signoff","detail":"director recheck signoff"},"chief",'director')
        self.assertEqual(signoff["status"],"closed")
        current=item
        for target in STATES[1:]:
            current=self.service.transition(current["id"],target,current["version"],"reviewer",TRANSITION_ROLES[target][0],reason="archive the event" if target==STATES[-1] else None)
        self.assertEqual(current["status"],STATES[-1])
        self.assertEqual(len(self.service.list_records(current["id"],"viewer")),2)
        events=self.service.audit("viewer",current["id"]); self.assertGreaterEqual(len(events),len(STATES)+3); self.assertTrue(self.repo.verify_audit_chain())
        actions=[event["action"] for event in events]
        for expected in ("create","record","review","signoff","transition"): self.assertIn(expected,actions)
        review_event=[event for event in events if event["action"]=="review"][0]
        self.assertEqual(review_event["actor"],"officer"); self.assertEqual(review_event["detail"]["comment"],"rectification verified"); self.assertTrue(review_event["created_at"])
        archive_event=[event for event in events if event["action"]=="transition" and event["detail"]["to"]==STATES[-1]][0]
        self.assertEqual(archive_event["detail"]["reason"],"archive the event"); self.assertTrue(archive_event["actor"]); self.assertTrue(archive_event["created_at"])
if __name__=="__main__": unittest.main()
