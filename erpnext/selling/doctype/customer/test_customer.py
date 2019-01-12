# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import unittest

from erpnext.accounts.party import get_due_date
from frappe.test_runner import make_test_records
from erpnext.exceptions import PartyFrozen, PartyDisabled
from frappe.utils import flt
from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding
from erpnext.tests.utils import create_test_contact_and_address

test_ignore = ["Price List"]
test_dependencies = ['Payment Term', 'Payment Terms Template']
test_records = frappe.get_test_records('Customer')

from six import iteritems

class TestCustomer(unittest.TestCase):
	def setUp(self):
		if not frappe.get_value('Item', '_Test Item'):
			make_test_records('Item')

	def tearDown(self):
		frappe.db.set_value("Customer", '_Test Customer', 'credit_limit', 0.0)

	def test_party_details(self):
		from erpnext.accounts.party import get_party_details

		to_check = {
			'selling_price_list': None,
			'customer_group': '_Test Customer Group',
			'contact_designation': None,
			'customer_address': '_Test Address for Customer-Office',
			'contact_department': None,
			'contact_email': 'test_contact_customer@example.com',
			'contact_mobile': None,
			'sales_team': [],
			'contact_display': '_Test Contact for _Test Customer',
			'contact_person': '_Test Contact for _Test Customer-_Test Customer',
			'territory': u'_Test Territory',
			'contact_phone': '+91 0000000000',
			'customer_name': '_Test Customer'
		}

		create_test_contact_and_address()

		frappe.db.set_value("Contact", "_Test Contact for _Test Customer-_Test Customer",
			"is_primary_contact", 1)

		details = get_party_details("_Test Customer")

		for key, value in iteritems(to_check):
			self.assertEqual(value, details.get(key))

	def test_party_details_tax_category(self):
		from erpnext.accounts.party import get_party_details

		frappe.delete_doc_if_exists("Address", "_Test Address With Tax Category-Billing")
		frappe.delete_doc_if_exists("Address", "_Test Address With Tax Category-Shipping")

		# Tax Category without Address
		details = get_party_details("_Test Customer With Tax Category")
		self.assertEqual(details.tax_category, "_Test Tax Category 1")

		billing_address = frappe.get_doc(dict(
			doctype='Address',
			address_title='_Test Address With Tax Category',
			tax_category='_Test Tax Category 2',
			address_type='Billing',
			address_line1='Station Road',
			city='_Test City',
			country='India',
			links=[dict(
				link_doctype='Customer',
				link_name='_Test Customer With Tax Category'
			)]
		)).insert()
		shipping_address = frappe.get_doc(dict(
			doctype='Address',
			address_title='_Test Address With Tax Category',
			tax_category='_Test Tax Category 3',
			address_type='Shipping',
			address_line1='Station Road',
			city='_Test City',
			country='India',
			links=[dict(
				link_doctype='Customer',
				link_name='_Test Customer With Tax Category'
			)]
		)).insert()

		settings = frappe.get_single("Accounts Settings")
		rollback_setting = settings.determine_address_tax_category_from

		# Tax Category from Billing Address
		settings.determine_address_tax_category_from = "Billing Address"
		settings.save()
		details = get_party_details("_Test Customer With Tax Category")
		self.assertEqual(details.tax_category, "_Test Tax Category 2")

		# Tax Category from Shipping Address
		settings.determine_address_tax_category_from = "Shipping Address"
		settings.save()
		details = get_party_details("_Test Customer With Tax Category")
		self.assertEqual(details.tax_category, "_Test Tax Category 3")

		# Rollback
		settings.determine_address_tax_category_from = rollback_setting
		settings.save()
		billing_address.delete()
		shipping_address.delete()

	def test_rename(self):
		# delete communication linked to these 2 customers
		for name in ("_Test Customer 1", "_Test Customer 1 Renamed"):
			frappe.db.sql("""delete from `tabCommunication`
				where communication_type='Comment' and reference_doctype=%s and reference_name=%s""",
				("Customer", name))

		# add comments
		comment = frappe.get_doc("Customer", "_Test Customer 1").add_comment("Comment", "Test Comment for Rename")

		# rename
		frappe.rename_doc("Customer", "_Test Customer 1", "_Test Customer 1 Renamed")

		# check if customer renamed
		self.assertTrue(frappe.db.exists("Customer", "_Test Customer 1 Renamed"))
		self.assertFalse(frappe.db.exists("Customer", "_Test Customer 1"))

		# test that comment gets linked to renamed doc
		self.assertEqual(frappe.db.get_value("Communication", {
			"communication_type": "Comment",
			"reference_doctype": "Customer",
			"reference_name": "_Test Customer 1 Renamed"
		}), comment.name)

		# rename back to original
		frappe.rename_doc("Customer", "_Test Customer 1 Renamed", "_Test Customer 1")

	def test_freezed_customer(self):
		make_test_records("Item")

		frappe.db.set_value("Customer", "_Test Customer", "is_frozen", 1)

		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order(do_not_save= True)

		self.assertRaises(PartyFrozen, so.save)

		frappe.db.set_value("Customer", "_Test Customer", "is_frozen", 0)

		so.save()

	def test_disabled_customer(self):
		make_test_records("Item")

		frappe.db.set_value("Customer", "_Test Customer", "disabled", 1)

		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order(do_not_save=True)

		self.assertRaises(PartyDisabled, so.save)

		frappe.db.set_value("Customer", "_Test Customer", "disabled", 0)

		so.save()

	def test_duplicate_customer(self):
		frappe.db.sql("delete from `tabCustomer` where customer_name='_Test Customer 1'")

		if not frappe.db.get_value("Customer", "_Test Customer 1"):
			test_customer_1 = frappe.get_doc(
				get_customer_dict('_Test Customer 1')).insert(ignore_permissions=True)
		else:
			test_customer_1 = frappe.get_doc("Customer", "_Test Customer 1")

		duplicate_customer = frappe.get_doc(
			get_customer_dict('_Test Customer 1')).insert(ignore_permissions=True)

		self.assertEqual("_Test Customer 1", test_customer_1.name)
		self.assertEqual("_Test Customer 1 - 1", duplicate_customer.name)
		self.assertEqual(test_customer_1.customer_name, duplicate_customer.customer_name)

	def get_customer_outstanding_amount(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		outstanding_amt = get_customer_outstanding('_Test Customer', '_Test Company')

		# If outstanding is negative make a transaction to get positive outstanding amount
		if outstanding_amt > 0.0:
			return outstanding_amt

		item_qty = int((abs(outstanding_amt) + 200)/100)
		make_sales_order(qty=item_qty)
		return get_customer_outstanding('_Test Customer', '_Test Company')

	def test_customer_credit_limit(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		outstanding_amt = self.get_customer_outstanding_amount()
		credit_limit = get_credit_limit('_Test Customer', '_Test Company')

		if outstanding_amt <= 0.0:
			item_qty = int((abs(outstanding_amt) + 200)/100)
			make_sales_order(qty=item_qty)

		if credit_limit == 0.0:
			frappe.db.set_value("Customer", '_Test Customer', 'credit_limit', outstanding_amt - 50.0)

		# Sales Order
		so = make_sales_order(do_not_submit=True)
		self.assertRaises(frappe.ValidationError, so.submit)

		# Delivery Note
		dn = create_delivery_note(do_not_submit=True)
		self.assertRaises(frappe.ValidationError, dn.submit)

		# Sales Invoice
		si = create_sales_invoice(do_not_submit=True)
		self.assertRaises(frappe.ValidationError, si.submit)

		if credit_limit > outstanding_amt:
			frappe.db.set_value("Customer", '_Test Customer', 'credit_limit', credit_limit)

		# Makes Sales invoice from Sales Order
		so.save(ignore_permissions=True)
		si = make_sales_invoice(so.name)
		si.save(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, make_sales_order)

	def test_customer_credit_limit_on_change(self):
		outstanding_amt = self.get_customer_outstanding_amount()
		customer = frappe.get_doc("Customer", '_Test Customer')
		customer.credit_limit = flt(outstanding_amt - 100)
		self.assertRaises(frappe.ValidationError, customer.save)

	def test_customer_payment_terms(self):
		frappe.db.set_value(
			"Customer", "_Test Customer With Template", "payment_terms", "_Test Payment Term Template 3")

		due_date = get_due_date("2016-01-22", "Customer", "_Test Customer With Template")
		self.assertEqual(due_date, "2016-02-21")

		due_date = get_due_date("2017-01-22", "Customer", "_Test Customer With Template")
		self.assertEqual(due_date, "2017-02-21")

		frappe.db.set_value(
			"Customer", "_Test Customer With Template", "payment_terms", "_Test Payment Term Template 1")

		due_date = get_due_date("2016-01-22", "Customer", "_Test Customer With Template")
		self.assertEqual(due_date, "2016-02-29")

		due_date = get_due_date("2017-01-22", "Customer", "_Test Customer With Template")
		self.assertEqual(due_date, "2017-02-28")

		frappe.db.set_value("Customer", "_Test Customer With Template", "payment_terms", "")

		# No default payment term template attached
		due_date = get_due_date("2016-01-22", "Customer", "_Test Customer")
		self.assertEqual(due_date, "2016-01-22")

		due_date = get_due_date("2017-01-22", "Customer", "_Test Customer")
		self.assertEqual(due_date, "2017-01-22")


def get_customer_dict(customer_name):
	return {
		 "customer_group": "_Test Customer Group",
		 "customer_name": customer_name,
		 "customer_type": "Individual",
		 "doctype": "Customer",
		 "territory": "_Test Territory"
	}
