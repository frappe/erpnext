# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.selling.doctype.customer.test_customer import make_customer
from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.stock.doctype.company_restriction.company_restriction import CompanyRestrictionError
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.tests.utils import ERPNextTestSuite


class TestCompanyRestriction(ERPNextTestSuite):
	def restrict_to_companies(self, doctype, name, companies):
		doc = frappe.get_doc(doctype, name)
		doc.restrict_to_companies = 1
		doc.set("allowed_companies", [])
		for company in companies:
			doc.append("allowed_companies", {"company": company})
		doc.save()

	def test_restricted_item_blocks_transaction_in_other_company(self):
		item = make_item()
		self.restrict_to_companies("Item", item.name, ["_Test Company 1"])

		self.assertRaises(CompanyRestrictionError, make_material_request, item_code=item.name)

		self.restrict_to_companies("Item", item.name, ["_Test Company 1", "_Test Company"])
		make_material_request(item_code=item.name)

	def test_restricted_customer_blocks_transaction_in_other_company(self):
		customer = make_customer("_Test Company Restricted Customer")
		self.restrict_to_companies("Customer", customer, ["_Test Company 1"])

		self.assertRaises(CompanyRestrictionError, make_quotation, party_name=customer, do_not_submit=1)

		self.restrict_to_companies("Customer", customer, ["_Test Company"])
		make_quotation(party_name=customer, do_not_submit=1)

	def test_restricted_supplier_blocks_transaction_in_other_company(self):
		supplier = create_supplier(supplier_name="_Test Company Restricted Supplier")
		self.restrict_to_companies("Supplier", supplier.name, ["_Test Company 1"])

		self.assertRaises(
			CompanyRestrictionError, create_purchase_order, supplier=supplier.name, do_not_submit=1
		)

		self.restrict_to_companies("Supplier", supplier.name, ["_Test Company"])
		create_purchase_order(supplier=supplier.name, do_not_submit=1)

	def test_unrestricted_item_is_not_blocked(self):
		item = make_item()
		make_material_request(item_code=item.name)

	def test_allowed_companies_is_mandatory_when_restricted(self):
		item = make_item()
		item.restrict_to_companies = 1
		self.assertRaises(frappe.MandatoryError, item.save)

	def test_exempt_doctypes_exist(self):
		from erpnext.stock.doctype.company_restriction.company_restriction import (
			COMPANY_RESTRICTION_EXEMPT_DOCTYPES,
		)

		for doctype in COMPANY_RESTRICTION_EXEMPT_DOCTYPES:
			self.assertTrue(frappe.db.exists("DocType", doctype), f"{doctype} is not a DocType")

	def test_cancel_works_after_restriction_change(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item()
		stock_entry = make_stock_entry(
			item_code=item.name, qty=5, to_warehouse="_Test Warehouse - _TC", rate=100
		)

		self.restrict_to_companies("Item", item.name, ["_Test Company 1"])
		stock_entry.reload()
		stock_entry.cancel()
