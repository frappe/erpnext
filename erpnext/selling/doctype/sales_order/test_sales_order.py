# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt
import frappe.permissions
import unittest
import copy

class TestSalesOrder(unittest.TestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_make_material_request(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_material_request

		so = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_material_request,
			so.name)

		sales_order = frappe.get_doc("Sales Order", so.name)
		sales_order.submit()
		mr = make_material_request(so.name)

		self.assertEquals(mr.material_request_type, "Purchase")
		self.assertEquals(len(mr.get("indent_details")), len(sales_order.get("sales_order_details")))

	def test_make_delivery_note(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

		so = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_delivery_note,
			so.name)

		sales_order = frappe.get_doc("Sales Order", so.name)
		sales_order.submit()
		dn = make_delivery_note(so.name)

		self.assertEquals(dn.doctype, "Delivery Note")
		self.assertEquals(len(dn.get("delivery_note_details")), len(sales_order.get("sales_order_details")))

	def test_make_sales_invoice(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		so = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_sales_invoice,
			so.name)

		sales_order = frappe.get_doc("Sales Order", so.name)
		sales_order.submit()
		si = make_sales_invoice(so.name)

		self.assertEquals(si.doctype, "Sales Invoice")
		self.assertEquals(len(si.get("entries")), len(sales_order.get("sales_order_details")))
		self.assertEquals(len(si.get("entries")), 1)

		si.posting_date = "2013-10-10"
		si.insert()
		si.submit()

		si1 = make_sales_invoice(so.name)
		self.assertEquals(len(si1.get("entries")), 0)


	def create_so(self, so_doc = None):
		if not so_doc:
			so_doc = test_records[0]

		w = frappe.copy_doc(so_doc)
		w.insert()
		w.submit()

		return w

	def create_dn_against_so(self, so, delivered_qty=0):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import test_records as dn_test_records
		from erpnext.stock.doctype.delivery_note.test_delivery_note import _insert_purchase_receipt

		_insert_purchase_receipt(so.get("sales_order_details")[0].item_code)

		dn = frappe.get_doc(frappe.copy_doc(dn_test_records[0]))
		dn.get("delivery_note_details")[0].item_code = so.get("sales_order_details")[0].item_code
		dn.get("delivery_note_details")[0].against_sales_order = so.name
		dn.get("delivery_note_details")[0].prevdoc_detail_docname = so.get("sales_order_details")[0].name
		if delivered_qty:
			dn.get("delivery_note_details")[0].qty = delivered_qty
		dn.insert()
		dn.submit()
		return dn

	def get_bin_reserved_qty(self, item_code, warehouse):
		return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse},
			"reserved_qty"))

	def delete_bin(self, item_code, warehouse):
		bin = frappe.db.exists({"doctype": "Bin", "item_code": item_code,
			"warehouse": warehouse})
		if bin:
			frappe.delete_doc("Bin", bin[0][0])

	def check_reserved_qty(self, item_code, warehouse, qty):
		bin_reserved_qty = self.get_bin_reserved_qty(item_code, warehouse)
		self.assertEqual(bin_reserved_qty, qty)

	def test_reserved_qty_for_so(self):
		# reset bin
		so_item = test_records[0]["sales_order_details"][0].copy()
		self.delete_bin(so_item["item_code"], so_item["warehouse"])

		# submit
		so = self.create_so()
		self.check_reserved_qty(so.get("sales_order_details")[0].item_code, so.get("sales_order_details")[0].warehouse, 10.0)

		# cancel
		so.cancel()
		self.check_reserved_qty(so.get("sales_order_details")[0].item_code, so.get("sales_order_details")[0].warehouse, 0.0)


	def test_reserved_qty_for_partial_delivery(self):
		# reset bin
		so_item = test_records[0]["sales_order_details"][0].copy()
		self.delete_bin(so_item["item_code"], so_item["warehouse"])

		# submit so
		so = self.create_so()

		# allow negative stock
		frappe.db.set_default("allow_negative_stock", 1)

		# submit dn
		dn = self.create_dn_against_so(so)

		self.check_reserved_qty(so.get("sales_order_details")[0].item_code, so.get("sales_order_details")[0].warehouse, 5.0)

		# stop so
		so.load_from_db()
		so.stop_sales_order()
		self.check_reserved_qty(so.get("sales_order_details")[0].item_code, so.get("sales_order_details")[0].warehouse, 0.0)

		# unstop so
		so.load_from_db()
		so.unstop_sales_order()
		self.check_reserved_qty(so.get("sales_order_details")[0].item_code, so.get("sales_order_details")[0].warehouse, 5.0)

		# cancel dn
		dn.cancel()
		self.check_reserved_qty(so.get("sales_order_details")[0].item_code, so.get("sales_order_details")[0].warehouse, 10.0)

	def test_reserved_qty_for_over_delivery(self):
		# reset bin
		so_item = test_records[0]["sales_order_details"][0].copy()
		self.delete_bin(so_item["item_code"], so_item["warehouse"])

		# submit so
		so = self.create_so()

		# allow negative stock
		frappe.db.set_default("allow_negative_stock", 1)

		# set over-delivery tolerance
		frappe.db.set_value('Item', so.get("sales_order_details")[0].item_code, 'tolerance', 50)

		# submit dn
		dn = self.create_dn_against_so(so, 15)
		self.check_reserved_qty(so.get("sales_order_details")[0].item_code, so.get("sales_order_details")[0].warehouse, 0.0)

		# cancel dn
		dn.cancel()
		self.check_reserved_qty(so.get("sales_order_details")[0].item_code, so.get("sales_order_details")[0].warehouse, 10.0)

	def test_reserved_qty_for_so_with_packing_list(self):
		from erpnext.selling.doctype.sales_bom.test_sales_bom import test_records as sbom_test_records

		# change item in test so record
		test_record = copy.deepcopy(test_records[0])
		test_record["sales_order_details"][0]["item_code"] = "_Test Sales BOM Item"

		# reset bin
		self.delete_bin(sbom_test_records[0]["sales_bom_items"][0]["item_code"], test_record.get("sales_order_details")[0]["warehouse"])
		self.delete_bin(sbom_test_records[0]["sales_bom_items"][1]["item_code"], test_record.get("sales_order_details")[0]["warehouse"])

		# submit
		so = self.create_so(test_record)


		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][0]["item_code"],
			so.get("sales_order_details")[0].warehouse, 50.0)
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][1]["item_code"],
			so.get("sales_order_details")[0].warehouse, 20.0)

		# cancel
		so.cancel()
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][0]["item_code"],
			so.get("sales_order_details")[0].warehouse, 0.0)
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][1]["item_code"],
			so.get("sales_order_details")[0].warehouse, 0.0)

	def test_reserved_qty_for_partial_delivery_with_packing_list(self):
		from erpnext.selling.doctype.sales_bom.test_sales_bom import test_records as sbom_test_records

		# change item in test so record

		test_record = frappe.copy_doc(test_records[0])
		test_record.get("sales_order_details")[0].item_code = "_Test Sales BOM Item"

		# reset bin
		self.delete_bin(sbom_test_records[0]["sales_bom_items"][0]["item_code"], test_record.get("sales_order_details")[0].warehouse)
		self.delete_bin(sbom_test_records[0]["sales_bom_items"][1]["item_code"], test_record.get("sales_order_details")[0].warehouse)

		# submit
		so = self.create_so(test_record)

		# allow negative stock
		frappe.db.set_default("allow_negative_stock", 1)

		# submit dn
		dn = self.create_dn_against_so(so)

		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][0]["item_code"],
			so.get("sales_order_details")[0].warehouse, 25.0)
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][1]["item_code"],
			so.get("sales_order_details")[0].warehouse, 10.0)

		# stop so
		so.load_from_db()
		so.stop_sales_order()

		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][0]["item_code"],
			so.get("sales_order_details")[0].warehouse, 0.0)
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][1]["item_code"],
			so.get("sales_order_details")[0].warehouse, 0.0)

		# unstop so
		so.load_from_db()
		so.unstop_sales_order()
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][0]["item_code"],
			so.get("sales_order_details")[0].warehouse, 25.0)
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][1]["item_code"],
			so.get("sales_order_details")[0].warehouse, 10.0)

		# cancel dn
		dn.cancel()
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][0]["item_code"],
			so.get("sales_order_details")[0].warehouse, 50.0)
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][1]["item_code"],
			so.get("sales_order_details")[0].warehouse, 20.0)

	def test_reserved_qty_for_over_delivery_with_packing_list(self):
		from erpnext.selling.doctype.sales_bom.test_sales_bom import test_records as sbom_test_records

		# change item in test so record
		test_record = frappe.copy_doc(test_records[0])
		test_record.get("sales_order_details")[0].item_code = "_Test Sales BOM Item"

		# reset bin
		self.delete_bin(sbom_test_records[0]["sales_bom_items"][0]["item_code"], test_record.get("sales_order_details")[0].warehouse)
		self.delete_bin(sbom_test_records[0]["sales_bom_items"][1]["item_code"], test_record.get("sales_order_details")[0].warehouse)

		# submit
		so = self.create_so(test_record)

		# allow negative stock
		frappe.db.set_default("allow_negative_stock", 1)

		# set over-delivery tolerance
		frappe.db.set_value('Item', so.get("sales_order_details")[0].item_code, 'tolerance', 50)

		# submit dn
		dn = self.create_dn_against_so(so, 15)

		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][0]["item_code"],
			so.get("sales_order_details")[0].warehouse, 0.0)
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][1]["item_code"],
			so.get("sales_order_details")[0].warehouse, 0.0)

		# cancel dn
		dn.cancel()
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][0]["item_code"],
			so.get("sales_order_details")[0].warehouse, 50.0)
		self.check_reserved_qty(sbom_test_records[0]["sales_bom_items"][1]["item_code"],
			so.get("sales_order_details")[0].warehouse, 20.0)

	def test_warehouse_user(self):
		frappe.permissions.add_user_permission("Warehouse", "_Test Warehouse 1 - _TC", "test@example.com")
		frappe.permissions.add_user_permission("Warehouse", "_Test Warehouse 2 - _TC1", "test2@example.com")
		frappe.permissions.add_user_permission("Company", "_Test Company 1", "test2@example.com")

		test_user = frappe.get_doc("User", "test@example.com")
		test_user.add_roles("Sales User", "Material User")
		test_user.remove_roles("Sales Manager")

		test_user_2 = frappe.get_doc("User", "test2@example.com")
		test_user_2.add_roles("Sales User", "Material User")
		test_user_2.remove_roles("Sales Manager")

		frappe.set_user("test@example.com")

		so = frappe.copy_doc(test_records[0])
		so.company = "_Test Company 1"
		so.conversion_rate = 0.02
		so.plc_conversion_rate = 0.02
		so.get("sales_order_details")[0].warehouse = "_Test Warehouse 2 - _TC1"
		self.assertRaises(frappe.PermissionError, so.insert)

		frappe.set_user("test2@example.com")
		so.insert()

		frappe.permissions.remove_user_permission("Warehouse", "_Test Warehouse 1 - _TC", "test@example.com")
		frappe.permissions.remove_user_permission("Warehouse", "_Test Warehouse 2 - _TC1", "test2@example.com")
		frappe.permissions.remove_user_permission("Company", "_Test Company 1", "test2@example.com")

	def test_block_delivery_note_against_cancelled_sales_order(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import _insert_purchase_receipt
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

		sales_order = frappe.copy_doc(test_records[0])
		sales_order.sales_order_details[0].qty = 5
		sales_order.insert()
		sales_order.submit()

		_insert_purchase_receipt(sales_order.get("sales_order_details")[0].item_code)

		delivery_note = make_delivery_note(sales_order.name)
		delivery_note.posting_date = sales_order.transaction_date
		delivery_note.insert()

		sales_order.cancel()

		self.assertRaises(frappe.CancelledLinkError, delivery_note.submit)

	def test_recurring_order(self):
		from frappe.utils import get_first_day, get_last_day, add_to_date, nowdate, getdate, add_days
		from erpnext.accounts.utils import get_fiscal_year
		today = nowdate()
		base_so = frappe.copy_doc(test_records[0])
		base_so.update({
			"convert_into_recurring_order": 1,
			"recurring_type": "Monthly",
			"notification_email_address": "test@example.com, test1@example.com, test2@example.com",
			"repeat_on_day_of_month": getdate(today).day,
			"transaction_date": today,
			"delivery_date": add_days(today, 15),
			"due_date": None,
			"fiscal_year": get_fiscal_year(today)[0],
			"order_period_from": get_first_day(today),
			"order_period_to": get_last_day(today)
		})

		# monthly
		so1 = frappe.copy_doc(base_so)
		so1.insert()
		so1.submit()
		self._test_recurring_order(so1, True)

		# monthly without a first and last day period
		so2 = frappe.copy_doc(base_so)
		so2.update({
			"order_period_from": today,
			"order_period_to": add_to_date(today, days=30)
		})
		so2.insert()
		so2.submit()
		self._test_recurring_order(so2, False)

		# quarterly
		so3 = frappe.copy_doc(base_so)
		so3.update({
			"recurring_type": "Quarterly",
			"order_period_from": get_first_day(today),
			"order_period_to": get_last_day(add_to_date(today, months=3))
		})
		so3.insert()
		so3.submit()
		self._test_recurring_order(so3, True)

		# quarterly without a first and last day period
		so4 = frappe.copy_doc(base_so)
		so4.update({
			"recurring_type": "Quarterly",
			"order_period_from": today,
			"order_period_to": add_to_date(today, months=3)
		})
		so4.insert()
		so4.submit()
		self._test_recurring_order(so4, False)

		# yearly
		so5 = frappe.copy_doc(base_so)
		so5.update({
			"recurring_type": "Yearly",
			"order_period_from": get_first_day(today),
			"order_period_to": get_last_day(add_to_date(today, years=1))
		})
		so5.insert()
		so5.submit()
		self._test_recurring_order(so5, True)

		# yearly without a first and last day period
		so6 = frappe.copy_doc(base_so)
		so6.update({
			"recurring_type": "Yearly",
			"order_period_from": today,
			"order_period_to": add_to_date(today, years=1)
		})
		so6.insert()
		so6.submit()
		self._test_recurring_order(so6, False)

		# change posting date but keep recuring day to be today
		so7 = frappe.copy_doc(base_so)
		so7.update({
			"transaction_date": add_to_date(today, days=-1)
		})
		so7.insert()
		so7.submit()

		# setting so that _test function works
		so7.transaction_date = today
		self._test_recurring_order(so7, True)

	def _test_recurring_order(self, base_so, first_and_last_day):
		from frappe.utils import add_months, get_last_day
		from erpnext.selling.doctype.sales_order.sales_order \
			import manage_recurring_orders, get_next_date

		no_of_months = ({"Monthly": 1, "Quarterly": 3, "Yearly": 12})[base_so.recurring_type]

		def _test(i):
			self.assertEquals(i+1, frappe.db.sql("""select count(*) from `tabSales Order`
				where recurring_id=%s and docstatus=1""", base_so.recurring_id)[0][0])

			next_date = get_next_date(base_so.transaction_date, no_of_months,
				base_so.repeat_on_day_of_month)

			manage_recurring_orders(next_date=next_date, commit=False)

			recurred_orders = frappe.db.sql("""select name from `tabSales Order`
				where recurring_id=%s and docstatus=1 order by name desc""",
				base_so.recurring_id)

			self.assertEquals(i+2, len(recurred_orders))

			new_so = frappe.get_doc("Sales Order", recurred_orders[0][0])

			print "New", new_so

			for fieldname in ["convert_into_recurring_order", "recurring_type",
				"repeat_on_day_of_month", "notification_email_address"]:
					self.assertEquals(base_so.get(fieldname),
						new_so.get(fieldname))

			self.assertEquals(new_so.transaction_date, unicode(next_date))

			self.assertEquals(new_so.order_period_from,
				unicode(add_months(base_so.order_period_from, no_of_months)))

			if first_and_last_day:
				self.assertEquals(new_so.order_period_to,
					unicode(get_last_day(add_months(base_so.order_period_to,
						no_of_months))))
			else:
				self.assertEquals(new_so.order_period_to,
					unicode(add_months(base_so.order_period_to, no_of_months)))

			return new_so

		# if yearly, test 1 repetition, else test 5 repetitions
		count = 1 if (no_of_months == 12) else 5
		for i in xrange(count):
			base_so = _test(i)

test_dependencies = ["Sales BOM", "Currency Exchange"]

test_records = frappe.get_test_records('Sales Order')
