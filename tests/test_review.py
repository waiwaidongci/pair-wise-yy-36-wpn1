import tempfile, unittest
from pathlib import Path
from src.domain import ConflictError, PermissionDenied, ValidationError
from src.repository import Repository
from src.service import Service
from src.rules import STATES, TRANSITION_ROLES
class ReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=Repository(str(Path(self.tmp.name)/"test.db")); self.service=Service(self.repo)
        self.item=self.service.create_item({"title":"review item","description":"review and signoff flow","severity":'exceedance',"quantity":8,"threshold":4,"external_ref":"REV-1"},"creator",'operator')
        self.record=self.service.add_record(self.item["id"],{"kind":"remediation","detail":"remediation registered","external_ref":"REV-R1"},"recorder",'operator')
    def tearDown(self): self.repo.close(); self.tmp.cleanup()
    def _advance_to_inspection(self):
        current=self.service.get_item(self.item["id"],"viewer")
        for target in STATES[1:-1]: current=self.service.transition(current["id"],target,current["version"],"reviewer",TRANSITION_ROLES[target][0])
        return current
    def test_registration_stays_pending_and_review_closes(self):
        self.assertEqual(self.record["status"],"open"); self.assertEqual(self.record["version"],1)
        with self.assertRaises(ValidationError): self.service.add_record(self.item["id"],{"kind":"remediation","detail":"premature close","status":"closed"},"recorder",'operator')
        with self.assertRaises(PermissionDenied): self.service.review_record(self.item["id"],self.record["id"],{"comment":"越权复核","expected_version":1},"recorder",'operator')
        closed=self.service.review_record(self.item["id"],self.record["id"],{"comment":"复核通过","expected_version":1},"officer",'compliance_officer')
        self.assertEqual(closed["status"],"closed"); self.assertEqual(closed["review_comment"],"复核通过"); self.assertEqual(closed["reviewed_by"],"officer"); self.assertIsNotNone(closed["reviewed_at"])
        events=[e for e in self.service.audit("viewer",self.item["id"]) if e["action"]=="review"]
        self.assertEqual(events[0]["actor"],"officer"); self.assertEqual(events[0]["detail"]["comment"],"复核通过")
    def test_stale_version_and_duplicate_review_prompt_refresh(self):
        with self.assertRaises(ConflictError): self.service.review_record(self.item["id"],self.record["id"],{"comment":"旧版本","expected_version":99},"officer",'compliance_officer')
        self.service.review_record(self.item["id"],self.record["id"],{"comment":"复核通过","expected_version":1},"officer",'compliance_officer')
        with self.assertRaises(ConflictError): self.service.review_record(self.item["id"],self.record["id"],{"comment":"重复关闭","expected_version":1},"officer",'compliance_officer')
        with self.assertRaises(ValidationError): self.service.review_record(self.item["id"],self.record["id"],{"expected_version":1},"officer",'compliance_officer')
    def test_director_signoff_only_once(self):
        with self.assertRaises(PermissionDenied): self.service.add_signoff(self.item["id"],{"comment":"越权签署"},"officer",'compliance_officer')
        signoff=self.service.add_signoff(self.item["id"],{"comment":"复查同意归档"},"chief",'director')
        self.assertEqual(signoff["comment"],"复查同意归档"); self.assertEqual(signoff["created_by"],"chief")
        with self.assertRaises(ConflictError): self.service.add_signoff(self.item["id"],{"comment":"重复签署"},"chief",'director')
        self.assertEqual(self.service.get_item(self.item["id"],"viewer")["signoff"]["created_by"],"chief")
    def test_archive_requires_review_signoff_and_reason(self):
        current=self._advance_to_inspection()
        with self.assertRaises(ValidationError): self.service.transition(current["id"],STATES[-1],current["version"],"chief",TRANSITION_ROLES[STATES[-1]][0])
        with self.assertRaises(ConflictError): self.service.transition(current["id"],STATES[-1],current["version"],"chief",TRANSITION_ROLES[STATES[-1]][0],"整改完成")
        self.service.review_record(self.item["id"],self.record["id"],{"comment":"复核通过","expected_version":1},"officer",'compliance_officer')
        with self.assertRaises(ConflictError): self.service.transition(current["id"],STATES[-1],current["version"],"chief",TRANSITION_ROLES[STATES[-1]][0],"整改完成")
        self.service.add_signoff(self.item["id"],{"comment":"复查同意归档"},"chief",'director')
        archived=self.service.transition(current["id"],STATES[-1],current["version"],"chief",TRANSITION_ROLES[STATES[-1]][0],"整改完成，同意归档")
        self.assertEqual(archived["status"],STATES[-1]); self.assertTrue(self.repo.verify_audit_chain())
if __name__=="__main__": unittest.main()
