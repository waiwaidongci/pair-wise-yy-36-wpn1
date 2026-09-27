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
        record=self.service.add_record(item["id"],{"kind":"evidence","detail":"evidence registered","external_ref":"EV-1"},"recorder",'operator')
        self.assertEqual(record["status"],"open")
        current=item
        for target in STATES[1:-1]:
            current=self.service.transition(current["id"],target,current["version"],"reviewer",TRANSITION_ROLES[target][0])
        closed=self.service.review_record(current["id"],record["id"],{"comment":"复核通过","expected_version":record["version"]},"officer",'compliance_officer')
        self.assertEqual(closed["status"],"closed"); self.assertEqual(closed["reviewed_by"],"officer")
        signoff=self.service.add_signoff(current["id"],{"comment":"复查同意归档"},"chief",'director')
        self.assertEqual(signoff["created_by"],"chief")
        current=self.service.transition(current["id"],STATES[-1],current["version"],"chief",TRANSITION_ROLES[STATES[-1]][0],"整改完成，同意归档")
        self.assertEqual(current["status"],STATES[-1])
        self.assertEqual(len(self.service.list_records(current["id"],"viewer")),1)
        events=self.service.audit("viewer",current["id"]); self.assertGreaterEqual(len(events),len(STATES)+3); self.assertTrue(self.repo.verify_audit_chain())
        archive=[e for e in events if e["action"]=="transition" and e["detail"].get("to")==STATES[-1]][0]
        self.assertEqual(archive["actor"],"chief"); self.assertEqual(archive["detail"]["reason"],"整改完成，同意归档")
if __name__=="__main__": unittest.main()
