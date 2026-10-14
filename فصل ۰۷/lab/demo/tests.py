from django.test import TestCase
from .models import PublicDocument
from .algorithms import Snowflake
class IdentifierTests(TestCase):
    def test_model_generates_distinct_uuid(self):
        a=PublicDocument.objects.create(title="a"); b=PublicDocument.objects.create(title="b")
        self.assertNotEqual(a.pk,b.pk)
    def test_sequence_and_clock_rollback(self):
        now=[Snowflake.EPOCH+10]; gen=Snowflake(7,clock_ms=lambda:now[0])
        values=[gen.next_id() for _ in range(4096)]
        self.assertEqual(len(set(values)),4096)
        self.assertEqual((values[0]>>12)&1023,7)
        with self.assertRaises(RuntimeError):gen.next_id()
        now[0]+=1; self.assertGreater(gen.next_id(),values[-1])
        now[0]-=2
        with self.assertRaises(RuntimeError):gen.next_id()
    def test_different_workers(self):
        clock=lambda:Snowflake.EPOCH+10
        self.assertNotEqual(Snowflake(1,clock).next_id(),Snowflake(2,clock).next_id())
