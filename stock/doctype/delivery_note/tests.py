import unittest
import webnotes

from webnotes.model.code import get_obj

class SubmissionTest(unittest.TestCase):
	def setUp(self):
		self.dn = webnotes.testing.create('Delivery Note')
		self.dn_items = []
		
		# get a line item for testing
		for d in self.dn.doclist:
			if d.doctype=='Delivery Note Detail':
				self.dn_items.append(d)
				
		self.old_bin = get_obj('Warehouse', self.line_item[0].warehouse).get_bin(self.line_item[0].item_code)
		self.dn.on_submit()

	def test_bin_is_updated(self):
		"tests if bin quantity is affected when on submission"
		bin = get_obj('Warehouse', self.line_item.warehouse).get_bin(self.line_item[0].item_code)
		self.assertTrue(bin.actual_qty == self.old_bin.actual_qty - self.line_item[0].qty)
		
	def test_sales_order_is_updated(self):
		"tests if"