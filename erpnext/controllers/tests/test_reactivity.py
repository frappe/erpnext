import frappe
from frappe import qb
from frappe.utils import today

from erpnext.tests.utils import ERPNextTestSuite


class TestReactivity(ERPNextTestSuite):
	def test_01_basic_item_details(self):
		# set Item Price
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": "_Test Item",
				"price_list": "Standard Selling",
				"price_list_rate": 90,
				"selling": True,
				"rate": 90,
				"valid_from": today(),
			}
		).insert()

		si = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"debit_to": "Debtors - _TC",
				"posting_date": today(),
				"cost_center": "Main - _TC",
				"currency": "INR",
				"conversion_rate": 1,
				"selling_price_list": "Standard Selling",
			}
		)
		itm = si.append("items")
		itm.item_code = "_Test Item"
		si.process_item_selection(itm.idx)
		self.assertEqual(itm.rate, 90)

		df = qb.DocType("DocField")
		_res = (
			qb.from_(df).select(df.fieldname).where(df.parent.eq("Sales Invoice Item") & df.reqd.eq(1)).run()
		)
		for field in _res:
			with self.subTest(field=field):
				self.assertIsNotNone(itm.get(field[0]))
		si.save().submit()
