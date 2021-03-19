from __future__ import unicode_literals

import frappe, unittest, datetime
from frappe.utils import getdate
from .tax_detail import execute, filter_match

class TestTaxDetail(unittest.TestCase):
	def setup(self):
		pass

	def test_filter_match(self):
		# None - treated as -inf number except range
		self.assertTrue(filter_match(None, '!='))
		self.assertTrue(filter_match(None, '<'))
		self.assertTrue(filter_match(None, '<jjj'))
		self.assertTrue(filter_match(None, '  :  '))
		self.assertTrue(filter_match(None, ':56'))
		self.assertTrue(filter_match(None, ':de'))
		self.assertFalse(filter_match(None, '3.4'))
		self.assertFalse(filter_match(None, '='))
		self.assertFalse(filter_match(None, '=3.4'))
		self.assertFalse(filter_match(None, '>3.4'))
		self.assertFalse(filter_match(None, '   <'))
		self.assertFalse(filter_match(None, 'ew'))
		self.assertFalse(filter_match(None, ' '))
		self.assertFalse(filter_match(None, ' f :'))

		# Numbers
		self.assertTrue(filter_match(3.4, '3.4'))
		self.assertTrue(filter_match(3.4, '.4'))
		self.assertTrue(filter_match(3.4, '3'))
		self.assertTrue(filter_match(-3.4, '< -3'))
		self.assertTrue(filter_match(-3.4, '> -4'))
		self.assertTrue(filter_match(3.4, '= 3.4 '))
		self.assertTrue(filter_match(3.4, '!=4.5'))
		self.assertTrue(filter_match(3.4, ' 3 : 4 '))
		self.assertTrue(filter_match(0.0, '  :  '))
		self.assertFalse(filter_match(3.4, '=4.5'))
		self.assertFalse(filter_match(3.4, ' = 3.4 '))
		self.assertFalse(filter_match(3.4, '!=3.4'))
		self.assertFalse(filter_match(3.4, '>6'))
		self.assertFalse(filter_match(3.4, '<-4.5'))
		self.assertFalse(filter_match(3.4, '4.5'))
		self.assertFalse(filter_match(3.4, '5:9'))

		# Strings
		self.assertTrue(filter_match('ACC-SINV-2021-00001', 'SINV'))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', 'sinv'))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', '-2021'))
		self.assertTrue(filter_match(' ACC-SINV-2021-00001', ' acc'))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', '=2021'))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', '!=zz'))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', '<   zzz  '))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', '  :  sinv  '))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '  sinv  :'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', ' acc'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '= 2021 '))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '!=sinv'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', ' >'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '>aa'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', ' <'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '<   '))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', ' ='))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '='))

		# Date - always match
		self.assertTrue(filter_match(datetime.date(2021, 3, 19), ' kdsjkldfs '))
