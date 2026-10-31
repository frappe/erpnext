# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.get_item_details import get_item_tax_template
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
TAX_ACCOUNT = "_Test Account VAT - _TC"


class TestItemTaxTemplate(ERPNextTestSuite):
	def make_template(self, rows, title="_Test ITT"):
		doc = frappe.new_doc("Item Tax Template")
		doc.title = f"{title} {frappe.generate_hash(length=6)}"
		doc.company = COMPANY
		for account, rate, not_applicable in rows:
			doc.append(
				"taxes",
				{"tax_type": account, "tax_rate": rate, "not_applicable": not_applicable},
			)
		return doc

	def make_tax_template(self, rate):
		return self.make_template([(TAX_ACCOUNT, rate, 0)]).insert().name

	def make_item_with_taxes(self, taxes):
		return make_item(properties={"taxes": taxes}).name

	def get_template_for(self, item_code, **kwargs):
		ctx = {"item_code": item_code, "company": COMPANY, "posting_date": today(), "tax_category": None}
		ctx.update(kwargs)
		return get_item_tax_template(ctx)

	def make_tax_category(self, title):
		if not frappe.db.exists("Tax Category", title):
			frappe.get_doc({"doctype": "Tax Category", "title": title}).insert()
		return title

	def test_dated_and_rate_band_rows_together(self):
		template_18 = self.make_tax_template(18)
		template_5 = self.make_tax_template(5)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_18, "valid_from": add_days(today(), -10)},
				{"item_tax_template": template_5, "minimum_net_rate": 0, "maximum_net_rate": 1000},
			]
		)

		self.assertEqual(self.get_template_for(item_code, base_net_rate=500), template_18)

	def test_rate_band_without_valid_from_on_backdated_transaction(self):
		template_5 = self.make_tax_template(5)
		template_12 = self.make_tax_template(12)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_5, "minimum_net_rate": 0, "maximum_net_rate": 1000},
				{"item_tax_template": template_12, "minimum_net_rate": 1000.01, "maximum_net_rate": 1000000},
			]
		)

		yesterday = add_days(today(), -1)
		self.assertEqual(
			self.get_template_for(item_code, posting_date=yesterday, base_net_rate=500), template_5
		)
		self.assertEqual(
			self.get_template_for(item_code, posting_date=yesterday, base_net_rate=5000), template_12
		)
