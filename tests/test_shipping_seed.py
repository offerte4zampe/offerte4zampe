import copy,json,pathlib,sqlite3,unittest
from automation.build_shipping_seed import convert,sql_seed,validate_intervals
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ShippingSeedTests(unittest.TestCase):
 def setUp(self):
  self.source=json.loads((ROOT/'site/data/shipping-rules.json').read_text());self.data=convert(self.source)
 def database(self):
  c=sqlite3.connect(':memory:');c.executescript((ROOT/'worker/schema/0002_shipping_rules.sql').read_text());return c
 def test_seed_executes_idempotently_and_preserves_unknowns(self):
  with self.database() as c:
   for _ in range(2):c.executescript(sql_seed(self.data))
   self.assertEqual(c.execute('select count(*) from shipping_rule').fetchone()[0],6)
   self.assertEqual(c.execute("select std_cents,free_from_cents,status from shipping_rule where shop_id='animaliapet'").fetchone(),(599,None,'verified'))
   self.assertEqual(c.execute("select threshold_mode,max_weight_g,verified_until from shipping_rule where shop_id='bauzaar'").fetchone(),('unknown',35000,self.source['merchants']['bauzaar']['verified_until']))
 def test_unmapped_fields_and_unrepresentable_units_are_rejected(self):
  for field,value in [('custom_exception',True),('fee',5.901),('boundary_unknown',58)]:
   source=copy.deepcopy(self.source);source['merchants']['bauzaar'][field]=value
   with self.assertRaises(ValueError):convert(source)
 def test_overlap_rejected_but_adjacent_versions_allowed(self):
  a=self.data['rules'][0];b={**a,'valid_from':self.data['rules'][0]['verified_until']}
  with self.assertRaises(ValueError):validate_intervals([a,b])
  validate_intervals([{**a,'valid_to':b['valid_from']},b])
  with self.database() as c:
   c.executescript(sql_seed(self.data))
   with self.assertRaisesRegex(sqlite3.IntegrityError,'overlapping'):c.executescript(sql_seed({'shops':[],'rules':[b]}))
 def test_constraints_reject_invalid_dates(self):
  with self.database() as c:
   c.executescript(sql_seed(self.data))
   with self.assertRaises(sqlite3.IntegrityError):c.execute("update shipping_rule set verified_until='invalid'")
 def test_expiry_required_and_old_observations_never_renewed(self):
  source=copy.deepcopy(self.source);source.pop('verification_max_age_days')
  for r in source['merchants'].values():r.pop('verified_until')
  with self.assertRaises(ValueError):convert(source)
  self.assertEqual(convert(self.source),self.data)
  self.assertEqual(sql_seed(self.data),(ROOT/'worker/seeds/shipping-rules.sql').read_text())
