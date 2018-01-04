import unittest, frappe, erpnext

@erpnext.allow_regional
def test_method():
	return 'original'

class TestInit(unittest.TestCase):
	def test_regional_overrides(self):
		frappe.flags.country = 'India'
		self.assertEqual(test_method(), 'overridden')

		frappe.flags.country = 'Nepal'
		self.assertEqual(test_method(), 'original')