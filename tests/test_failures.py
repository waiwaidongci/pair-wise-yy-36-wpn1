import tempfile, unittest
from pathlib import Path
from src.domain import ConflictError, PermissionDenied, ValidationError
from src.repository import Repository
from src.service import Service
from src.rules import STATES, TRANSITION_ROLES
class FailureTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=Repository(str(Path(self.tmp.name)/"test.db")); self.service=Service(self.repo)
        self.item=self.service.create_item({"title":"failure item","description":"failure scenarios","severity":'exceedance',"quantity":5,"threshold":10,"external_ref":"FAIL-1"},"creator",'operator')
    def tearDown(self): self.repo.close(); self.tmp.cleanup()
    def _reach_inspection(self):
        current=self.service.get_item(self.item["id"],"viewer")
        for target in STATES[1:-1]: current=self.service.transition(current["id"],target,current["version"],"reviewer",TRANSITION_ROLES[target][0])
        return current
    def test_permission_version_duplicate_and_invariant(self):
        with self.assertRaises(PermissionDenied): self.service.transition(self.item["id"],STATES[1],1,"attacker","viewer")
        with self.assertRaises(ConflictError): self.service.transition(self.item["id"],STATES[1],99,"reviewer",TRANSITION_ROLES[STATES[1]][0])
        payload={"kind":"action","detail":"same reference","external_ref":"DUP-1"}
        self.service.add_record(self.item["id"],payload,"recorder",'operator')
        with self.assertRaises(ConflictError): self.service.add_record(self.item["id"],payload,"recorder",'operator')
        current=self._reach_inspection()
        with self.assertRaises(ConflictError): self.service.transition(current["id"],STATES[-1],current["version"],"reviewer",TRANSITION_ROLES[STATES[-1]][0],reason="archive")
    def test_review_close_guards(self):
        record=self.service.add_record(self.item["id"],{"kind":"remediation","detail":"fix the leak"},"recorder",'operator')
        self.assertEqual(record["status"],"pending_review")
        with self.assertRaises(PermissionDenied): self.service.review_record(self.item["id"],record["id"],{"comment":"ok","expected_version":record["version"]},"recorder",'operator')
        with self.assertRaises(ValidationError): self.service.review_record(self.item["id"],record["id"],{"expected_version":record["version"]},"officer",'compliance_officer')
        with self.assertRaises(ConflictError): self.service.review_record(self.item["id"],record["id"],{"comment":"ok","expected_version":99},"officer",'compliance_officer')
        closed=self.service.review_record(self.item["id"],record["id"],{"comment":"verified","expected_version":record["version"]},"officer",'compliance_officer')
        self.assertEqual(closed["status"],"closed")
        with self.assertRaises(ConflictError): self.service.review_record(self.item["id"],record["id"],{"comment":"again","expected_version":closed["version"]},"officer",'compliance_officer')
    def test_signoff_guards(self):
        with self.assertRaises(PermissionDenied): self.service.add_record(self.item["id"],{"kind":"director_signoff","detail":"not allowed"},"recorder",'operator')
        with self.assertRaises(PermissionDenied): self.service.add_record(self.item["id"],{"kind":"remediation","detail":"director cannot register"},"chief",'director')
        signoff=self.service.add_record(self.item["id"],{"kind":"director_signoff","detail":"director recheck"},"chief",'director')
        self.assertEqual(signoff["status"],"closed")
        with self.assertRaises(ConflictError): self.service.add_record(self.item["id"],{"kind":"director_signoff","detail":"again"},"chief",'director')
    def test_archive_requires_signoff_and_reason(self):
        record=self.service.add_record(self.item["id"],{"kind":"remediation","detail":"fix"},"recorder",'operator')
        self.service.review_record(self.item["id"],record["id"],{"comment":"verified","expected_version":record["version"]},"officer",'compliance_officer')
        current=self._reach_inspection()
        with self.assertRaises(ValidationError): self.service.transition(current["id"],STATES[-1],current["version"],"chief",'director')
        with self.assertRaises(ConflictError): self.service.transition(current["id"],STATES[-1],current["version"],"chief",'director',reason="archive")
        self.service.add_record(self.item["id"],{"kind":"director_signoff","detail":"director recheck"},"chief",'director')
        archived=self.service.transition(current["id"],STATES[-1],current["version"],"chief",'director',reason="all remediation verified")
        self.assertEqual(archived["status"],STATES[-1])
if __name__=="__main__": unittest.main()
