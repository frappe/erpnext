# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, unittest
import frappe.defaults
from frappe.utils import flt, getdate
from erpnext.stock.doctype.serial_no.serial_no import *
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import StockFreezeError

def get_sle(**args):
	condition, values = "", []
	for key, value in args.iteritems():
		condition += " and " if condition else " where "
		condition += "`{0}`=%s".format(key)
		values.append(value)

	return frappe.db.sql("""select * from `tabStock Ledger Entry` %s
		order by timestamp(posting_date, posting_time) desc, name desc limit 1"""% condition,
		values, as_dict=1)

def make_zero(item_code, warehouse):
	sle = get_sle(item_code = item_code, warehouse = warehouse)
	qty = sle[0].qty_after_transaction if sle else 0
	if qty < 0:
		make_stock_entry(item_code, None, warehouse, abs(qty), incoming_rate=10)
	elif qty > 0:
		make_stock_entry(item_code, warehouse, None, qty, incoming_rate=10)

class TestStockEntry(unittest.TestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		set_perpetual_inventory(0)
		if hasattr(self, "old_default_company"):
			frappe.db.set_default("company", self.old_default_company)

	def test_fifo(self):
		frappe.db.set_default("allow_negative_stock", 1)
		item_code = "_Test Item 2"
		warehouse = "_Test Warehouse - _TC"
		make_zero(item_code, warehouse)

		make_stock_entry(item_code, None, warehouse, 1, incoming_rate=10)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]

		self.assertEqual([[1, 10]], eval(sle.stock_queue))

		# negative qty
		make_zero(item_code, warehouse)
		make_stock_entry(item_code, warehouse, None, 1, incoming_rate=10)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]

		self.assertEqual([[-1, 10]], eval(sle.stock_queue))

		# further negative
		make_stock_entry(item_code, warehouse, None, 1)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]

		self.assertEqual([[-2, 10]], eval(sle.stock_queue))

		# move stock to positive
		make_stock_entry(item_code, None, warehouse, 3, incoming_rate=10)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]

		self.assertEqual([[1, 10]], eval(sle.stock_queue))

		frappe.db.set_default("allow_negative_stock", 0)

	def test_auto_material_request(self):
		frappe.db.sql("""delete from `tabMaterial Request Item`""")
		frappe.db.sql("""delete from `tabMaterial Request`""")
		self._clear_stock_account_balance()

		frappe.db.set_value("Stock Settings", None, "auto_indent", 1)

		st1 = frappe.copy_doc(test_records[0])
		st1.insert()
		st1.submit()
		st2 = frappe.copy_doc(test_records[1])
		st2.insert()
		st2.submit()

		from erpnext.stock.utils import reorder_item
		reorder_item()

		mr_name = frappe.db.sql("""select parent from `tabMaterial Request Item`
			where item_code='_Test Item'""")

		self.assertTrue(mr_name)

	def test_material_receipt_gl_entry(self):
		self._clear_stock_account_balance()
		set_perpetual_inventory()

		mr = frappe.copy_doc(test_records[0])
		mr.insert()
		mr.submit()

		stock_in_hand_account = frappe.db.get_value("Account", {"account_type": "Warehouse",
			"master_name": mr.get("mtn_details")[0].t_warehouse})

		self.check_stock_ledger_entries("Stock Entry", mr.name,
			[["_Test Item", "_Test Warehouse - _TC", 50.0]])

		self.check_gl_entries("Stock Entry", mr.name,
			sorted([
				[stock_in_hand_account, 5000.0, 0.0],
				["Stock Adjustment - _TC", 0.0, 5000.0]
			])
		)

		mr.cancel()

		self.assertFalse(frappe.db.sql("""select * from `tabStock Ledger Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mr.name))

		self.assertFalse(frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mr.name))


	def test_material_issue_gl_entry(self):
		self._clear_stock_account_balance()
		set_perpetual_inventory()

		self._insert_material_receipt()

		mi = frappe.copy_doc(test_records[1])
		mi.insert()
		mi.submit()

		self.check_stock_ledger_entries("Stock Entry", mi.name,
			[["_Test Item", "_Test Warehouse - _TC", -40.0]])

		stock_in_hand_account = frappe.db.get_value("Account", {"account_type": "Warehouse",
			"master_name": mi.get("mtn_details")[0].s_warehouse})

		self.check_gl_entries("Stock Entry", mi.name,
			sorted([
				[stock_in_hand_account, 0.0, 4000.0],
				["Stock Adjustment - _TC", 4000.0, 0.0]
			])
		)

		mi.cancel()
		self.assertFalse(frappe.db.sql("""select * from `tabStock Ledger Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mi.name))

		self.assertFalse(frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mi.name))

		self.assertEquals(frappe.db.get_value("Bin", {"warehouse": mi.get("mtn_details")[0].s_warehouse,
			"item_code": mi.get("mtn_details")[0].item_code}, "actual_qty"), 50)

		self.assertEquals(frappe.db.get_value("Bin", {"warehouse": mi.get("mtn_details")[0].s_warehouse,
			"item_code": mi.get("mtn_details")[0].item_code}, "stock_value"), 5000)

	def test_material_transfer_gl_entry(self):
		self._clear_stock_account_balance()
		set_perpetual_inventory()

		self._insert_material_receipt()

		mtn = frappe.copy_doc(test_records[2])
		mtn.insert()
		mtn.submit()

		self.check_stock_ledger_entries("Stock Entry", mtn.name,
			[["_Test Item", "_Test Warehouse - _TC", -45.0], ["_Test Item", "_Test Warehouse 1 - _TC", 45.0]])

		stock_in_hand_account = frappe.db.get_value("Account", {"account_type": "Warehouse",
			"master_name": mtn.get("mtn_details")[0].s_warehouse})

		fixed_asset_account = frappe.db.get_value("Account", {"account_type": "Warehouse",
			"master_name": mtn.get("mtn_details")[0].t_warehouse})


		self.check_gl_entries("Stock Entry", mtn.name,
			sorted([
				[stock_in_hand_account, 0.0, 4500.0],
				[fixed_asset_account, 4500.0, 0.0],
			])
		)


		mtn.cancel()
		self.assertFalse(frappe.db.sql("""select * from `tabStock Ledger Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mtn.name))

		self.assertFalse(frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mtn.name))


	def test_repack_no_change_in_valuation(self):
		self._clear_stock_account_balance()
		set_perpetual_inventory()

		self._insert_material_receipt()

		repack = frappe.copy_doc(test_records[3])
		repack.insert()
		repack.submit()

		self.check_stock_ledger_entries("Stock Entry", repack.name,
			[["_Test Item", "_Test Warehouse - _TC", -50.0],
				["_Test Item Home Desktop 100", "_Test Warehouse - _TC", 1]])

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Stock Entry' and voucher_no=%s
			order by account desc""", repack.name, as_dict=1)
		self.assertFalse(gl_entries)

		set_perpetual_inventory(0)

	def test_repack_with_change_in_valuation(self):
		self._clear_stock_account_balance()
		set_perpetual_inventory()

		self._insert_material_receipt()

		repack = frappe.copy_doc(test_records[3])
		repack.get("mtn_details")[1].incoming_rate = 6000
		repack.insert()
		repack.submit()

		stock_in_hand_account = frappe.db.get_value("Account", {"account_type": "Warehouse",
			"master_name": repack.get("mtn_details")[1].t_warehouse})

		self.check_gl_entries("Stock Entry", repack.name,
			sorted([
				[stock_in_hand_account, 1000.0, 0.0],
				["Stock Adjustment - _TC", 0.0, 1000.0],
			])
		)
		set_perpetual_inventory(0)

	def check_stock_ledger_entries(self, voucher_type, voucher_no, expected_sle):
		expected_sle.sort(key=lambda x: x[0])

		# check stock ledger entries
		sle = frappe.db.sql("""select item_code, warehouse, actual_qty
			from `tabStock Ledger Entry` where voucher_type = %s
			and voucher_no = %s order by item_code, warehouse, actual_qty""",
			(voucher_type, voucher_no), as_list=1)
		self.assertTrue(sle)
		sle.sort(key=lambda x: x[0])

		for i, sle in enumerate(sle):
			self.assertEquals(expected_sle[i][0], sle[0])
			self.assertEquals(expected_sle[i][1], sle[1])
			self.assertEquals(expected_sle[i][2], sle[2])

	def check_gl_entries(self, voucher_type, voucher_no, expected_gl_entries):
		expected_gl_entries.sort(key=lambda x: x[0])

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type=%s and voucher_no=%s
			order by account asc, debit asc""", (voucher_type, voucher_no), as_list=1)
		self.assertTrue(gl_entries)
		gl_entries.sort(key=lambda x: x[0])

		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_gl_entries[i][0], gle[0])
			self.assertEquals(expected_gl_entries[i][1], gle[1])
			self.assertEquals(expected_gl_entries[i][2], gle[2])

	def _insert_material_receipt(self):
		self._clear_stock_account_balance()
		se1 = frappe.copy_doc(test_records[0])
		se1.insert()
		se1.submit()

		se2 = frappe.copy_doc(test_records[0])
		se2.get("mtn_details")[0].item_code = "_Test Item Home Desktop 100"
		se2.insert()
		se2.submit()

		frappe.db.set_default("company", self.old_default_company)

	def _get_actual_qty(self):
		return flt(frappe.db.get_value("Bin", {"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC"}, "actual_qty"))

	def _test_sales_invoice_return(self, item_code, delivered_qty, returned_qty):
		from erpnext.stock.doctype.stock_entry.stock_entry import NotUpdateStockError

		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice \
			import test_records as sales_invoice_test_records

		# invalid sales invoice as update stock not checked
		si = frappe.copy_doc(sales_invoice_test_records[1])
		si.insert()
		si.submit()

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Sales Return"
		se.sales_invoice_no = si.name
		se.get("mtn_details")[0].qty = returned_qty
		se.get("mtn_details")[0].transfer_qty = returned_qty
		self.assertRaises(NotUpdateStockError, se.insert)

		self._insert_material_receipt()

		# check currency available qty in bin
		actual_qty_0 = self._get_actual_qty()

		# insert a pos invoice with update stock
		si = frappe.copy_doc(sales_invoice_test_records[1])
		si.update_stock = 1
		si.get("entries")[0].warehouse = "_Test Warehouse - _TC"
		si.get("entries")[0].item_code = item_code
		si.get("entries")[0].qty = 5.0
		si.insert()
		si.submit()

		# check available bin qty after invoice submission
		actual_qty_1 = self._get_actual_qty()

		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)

		# check if item is validated
		se = frappe.copy_doc(test_records[0])
		se.purpose = "Sales Return"
		se.sales_invoice_no = si.name
		se.posting_date = "2013-03-10"
		se.fiscal_year = "_Test Fiscal Year 2013"
		se.get("mtn_details")[0].item_code = "_Test Item Home Desktop 200"
		se.get("mtn_details")[0].qty = returned_qty
		se.get("mtn_details")[0].transfer_qty = returned_qty

		# check if stock entry gets submitted
		self.assertRaises(frappe.DoesNotExistError, se.insert)

		# try again
		se = frappe.copy_doc(test_records[0])
		se.purpose = "Sales Return"
		se.posting_date = "2013-03-10"
		se.fiscal_year = "_Test Fiscal Year 2013"
		se.sales_invoice_no = si.name
		se.get("mtn_details")[0].qty = returned_qty
		se.get("mtn_details")[0].transfer_qty = returned_qty
		# in both cases item code remains _Test Item when returning
		se.insert()

		se.submit()

		# check if available qty is increased
		actual_qty_2 = self._get_actual_qty()

		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)

		return se

	def test_sales_invoice_return_of_non_packing_item(self):
		self._clear_stock_account_balance()
		self._test_sales_invoice_return("_Test Item", 5, 2)

	def test_sales_invoice_return_of_packing_item(self):
		self._clear_stock_account_balance()
		self._test_sales_invoice_return("_Test Sales BOM Item", 25, 20)

	def _test_delivery_note_return(self, item_code, delivered_qty, returned_qty):
		self._insert_material_receipt()

		from erpnext.stock.doctype.delivery_note.test_delivery_note \
			import test_records as delivery_note_test_records

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		actual_qty_0 = self._get_actual_qty()
		# make a delivery note based on this invoice
		dn = frappe.copy_doc(delivery_note_test_records[0])
		dn.get("delivery_note_details")[0].item_code = item_code
		dn.insert()
		dn.submit()

		actual_qty_1 = self._get_actual_qty()

		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)

		si_doc = make_sales_invoice(dn.name)

		si = frappe.get_doc(si_doc)
		si.posting_date = dn.posting_date
		si.debit_to = "_Test Customer - _TC"
		for d in si.get("entries"):
			d.income_account = "Sales - _TC"
			d.cost_center = "_Test Cost Center - _TC"
		si.insert()
		si.submit()

		# insert and submit stock entry for sales return
		se = frappe.copy_doc(test_records[0])
		se.purpose = "Sales Return"
		se.delivery_note_no = dn.name
		se.posting_date = "2013-03-10"
		se.fiscal_year = "_Test Fiscal Year 2013"
		se.get("mtn_details")[0].qty = se.get("mtn_details")[0].transfer_qty = returned_qty

		se.insert()
		se.submit()

		actual_qty_2 = self._get_actual_qty()
		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)

		return se

	def test_delivery_note_return_of_non_packing_item(self):
		self._clear_stock_account_balance()
		self._test_delivery_note_return("_Test Item", 5, 2)

	def test_delivery_note_return_of_packing_item(self):
		self._clear_stock_account_balance()
		self._test_delivery_note_return("_Test Sales BOM Item", 25, 20)

	def _test_sales_return_jv(self, se):
		from erpnext.stock.doctype.stock_entry.stock_entry import make_return_jv
		jv = make_return_jv(se.name)

		self.assertEqual(len(jv.get("entries")), 2)
		self.assertEqual(jv.get("voucher_type"), "Credit Note")
		self.assertEqual(jv.get("posting_date"), se.posting_date)
		self.assertEqual(jv.get("entries")[0].get("account"), "_Test Customer - _TC")
		self.assertEqual(jv.get("entries")[1].get("account"), "Sales - _TC")
		self.assertTrue(jv.get("entries")[0].get("against_invoice"))

	def test_make_return_jv_for_sales_invoice_non_packing_item(self):
		self._clear_stock_account_balance()
		se = self._test_sales_invoice_return("_Test Item", 5, 2)
		self._test_sales_return_jv(se)

	def test_make_return_jv_for_sales_invoice_packing_item(self):
		self._clear_stock_account_balance()
		se = self._test_sales_invoice_return("_Test Sales BOM Item", 25, 20)
		self._test_sales_return_jv(se)

	def test_make_return_jv_for_delivery_note_non_packing_item(self):
		self._clear_stock_account_balance()
		se = self._test_delivery_note_return("_Test Item", 5, 2)
		self._test_sales_return_jv(se)

		se = self._test_delivery_note_return_against_sales_order("_Test Item", 5, 2)
		self._test_sales_return_jv(se)

	def test_make_return_jv_for_delivery_note_packing_item(self):
		self._clear_stock_account_balance()
		se = self._test_delivery_note_return("_Test Sales BOM Item", 25, 20)
		self._test_sales_return_jv(se)

		se = self._test_delivery_note_return_against_sales_order("_Test Sales BOM Item", 25, 20)
		self._test_sales_return_jv(se)

	def _test_delivery_note_return_against_sales_order(self, item_code, delivered_qty, returned_qty):
		self._insert_material_receipt()

		from erpnext.selling.doctype.sales_order.test_sales_order import test_records as sales_order_test_records
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice, make_delivery_note

		actual_qty_0 = self._get_actual_qty()

		so = frappe.copy_doc(sales_order_test_records[0])
		so.get("sales_order_details")[0].item_code = item_code
		so.get("sales_order_details")[0].qty = 5.0
		so.insert()
		so.submit()

		dn = make_delivery_note(so.name)
		dn.status = "Draft"
		dn.posting_date = so.delivery_date
		dn.insert()
		dn.submit()

		actual_qty_1 = self._get_actual_qty()
		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)

		si = make_sales_invoice(so.name)
		si.posting_date = dn.posting_date
		si.debit_to = "_Test Customer - _TC"
		for d in si.get("entries"):
			d.income_account = "Sales - _TC"
			d.cost_center = "_Test Cost Center - _TC"
		si.insert()
		si.submit()

		# insert and submit stock entry for sales return
		se = frappe.copy_doc(test_records[0])
		se.purpose = "Sales Return"
		se.delivery_note_no = dn.name
		se.posting_date = "2013-03-10"
		se.fiscal_year = "_Test Fiscal Year 2013"
		se.get("mtn_details")[0].qty = se.get("mtn_details")[0].transfer_qty = returned_qty

		se.insert()
		se.submit()

		actual_qty_2 = self._get_actual_qty()
		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)

		return se

	def test_purchase_receipt_return(self):
		self._clear_stock_account_balance()

		actual_qty_0 = self._get_actual_qty()

		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt \
			import test_records as purchase_receipt_test_records

		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		# submit purchase receipt
		pr = frappe.copy_doc(purchase_receipt_test_records[0])
		pr.insert()
		pr.submit()

		actual_qty_1 = self._get_actual_qty()

		self.assertEquals(actual_qty_0 + 5, actual_qty_1)

		pi_doc = make_purchase_invoice(pr.name)

		pi = frappe.get_doc(pi_doc)
		pi.posting_date = pr.posting_date
		pi.credit_to = "_Test Supplier - _TC"
		for d in pi.get("entries"):
			d.expense_account = "_Test Account Cost for Goods Sold - _TC"
			d.cost_center = "_Test Cost Center - _TC"

		for d in pi.get("other_charges"):
			d.cost_center = "_Test Cost Center - _TC"

		pi.run_method("calculate_taxes_and_totals")
		pi.bill_no = "NA"
		pi.insert()
		pi.submit()

		# submit purchase return
		se = frappe.copy_doc(test_records[0])
		se.purpose = "Purchase Return"
		se.purchase_receipt_no = pr.name
		se.posting_date = "2013-03-01"
		se.fiscal_year = "_Test Fiscal Year 2013"
		se.get("mtn_details")[0].qty = se.get("mtn_details")[0].transfer_qty = 5
		se.get("mtn_details")[0].s_warehouse = "_Test Warehouse - _TC"
		se.insert()
		se.submit()

		actual_qty_2 = self._get_actual_qty()

		self.assertEquals(actual_qty_1 - 5, actual_qty_2)

		frappe.db.set_default("company", self.old_default_company)

		return se, pr.name

	def test_over_stock_return(self):
		from erpnext.stock.doctype.stock_entry.stock_entry import StockOverReturnError
		self._clear_stock_account_balance()

		# out of 10, 5 gets returned
		prev_se, pr_docname = self.test_purchase_receipt_return()

		# submit purchase return - return another 6 qtys so that exception is raised
		se = frappe.copy_doc(test_records[0])
		se.purpose = "Purchase Return"
		se.purchase_receipt_no = pr_docname
		se.posting_date = "2013-03-01"
		se.fiscal_year = "_Test Fiscal Year 2013"
		se.get("mtn_details")[0].qty = se.get("mtn_details")[0].transfer_qty = 6
		se.get("mtn_details")[0].s_warehouse = "_Test Warehouse - _TC"

		self.assertRaises(StockOverReturnError, se.insert)

	def _test_purchase_return_jv(self, se):
		from erpnext.stock.doctype.stock_entry.stock_entry import make_return_jv
		jv = make_return_jv(se.name)

		self.assertEqual(len(jv.get("entries")), 2)
		self.assertEqual(jv.get("voucher_type"), "Debit Note")
		self.assertEqual(jv.get("posting_date"), se.posting_date)
		self.assertEqual(jv.get("entries")[0].get("account"), "_Test Supplier - _TC")
		self.assertEqual(jv.get("entries")[1].get("account"), "_Test Account Cost for Goods Sold - _TC")
		self.assertTrue(jv.get("entries")[0].get("against_voucher"))

	def test_make_return_jv_for_purchase_receipt(self):
		self._clear_stock_account_balance()
		se, pr_name = self.test_purchase_receipt_return()
		self._test_purchase_return_jv(se)

		se, pr_name = self._test_purchase_return_return_against_purchase_order()
		self._test_purchase_return_jv(se)

	def _test_purchase_return_return_against_purchase_order(self):
		self._clear_stock_account_balance()

		actual_qty_0 = self._get_actual_qty()

		from erpnext.buying.doctype.purchase_order.test_purchase_order \
			import test_records as purchase_order_test_records

		from erpnext.buying.doctype.purchase_order.purchase_order import \
			make_purchase_receipt, make_purchase_invoice

		# submit purchase receipt
		po = frappe.copy_doc(purchase_order_test_records[0])
		po.is_subcontracted = None
		po.get("po_details")[0].item_code = "_Test Item"
		po.get("po_details")[0].rate = 50
		po.insert()
		po.submit()

		pr_doc = make_purchase_receipt(po.name)

		pr = frappe.get_doc(pr_doc)
		pr.posting_date = po.transaction_date
		pr.insert()
		pr.submit()

		actual_qty_1 = self._get_actual_qty()

		self.assertEquals(actual_qty_0 + 10, actual_qty_1)

		pi_doc = make_purchase_invoice(po.name)

		pi = frappe.get_doc(pi_doc)
		pi.posting_date = pr.posting_date
		pi.credit_to = "_Test Supplier - _TC"
		for d in pi.get("entries"):
			d.expense_account = "_Test Account Cost for Goods Sold - _TC"
			d.cost_center = "_Test Cost Center - _TC"
		for d in pi.get("other_charges"):
			d.cost_center = "_Test Cost Center - _TC"

		pi.run_method("calculate_taxes_and_totals")
		pi.bill_no = "NA"
		pi.insert()
		pi.submit()

		# submit purchase return
		se = frappe.copy_doc(test_records[0])
		se.purpose = "Purchase Return"
		se.purchase_receipt_no = pr.name
		se.posting_date = "2013-03-01"
		se.fiscal_year = "_Test Fiscal Year 2013"
		se.get("mtn_details")[0].qty = se.get("mtn_details")[0].transfer_qty = 5
		se.get("mtn_details")[0].s_warehouse = "_Test Warehouse - _TC"
		se.insert()
		se.submit()

		actual_qty_2 = self._get_actual_qty()

		self.assertEquals(actual_qty_1 - 5, actual_qty_2)

		frappe.db.set_default("company", self.old_default_company)

		return se, pr.name

	def _clear_stock_account_balance(self):
		frappe.db.sql("delete from `tabStock Ledger Entry`")
		frappe.db.sql("""delete from `tabBin`""")
		frappe.db.sql("""delete from `tabGL Entry`""")

		self.old_default_company = frappe.db.get_default("company")
		frappe.db.set_default("company", "_Test Company")

	def test_serial_no_not_reqd(self):
		se = frappe.copy_doc(test_records[0])
		se.get("mtn_details")[0].serial_no = "ABCD"
		se.insert()
		self.assertRaises(SerialNoNotRequiredError, se.submit)

	def test_serial_no_reqd(self):
		se = frappe.copy_doc(test_records[0])
		se.get("mtn_details")[0].item_code = "_Test Serialized Item"
		se.get("mtn_details")[0].qty = 2
		se.get("mtn_details")[0].transfer_qty = 2
		se.insert()
		self.assertRaises(SerialNoRequiredError, se.submit)

	def test_serial_no_qty_more(self):
		se = frappe.copy_doc(test_records[0])
		se.get("mtn_details")[0].item_code = "_Test Serialized Item"
		se.get("mtn_details")[0].qty = 2
		se.get("mtn_details")[0].serial_no = "ABCD\nEFGH\nXYZ"
		se.get("mtn_details")[0].transfer_qty = 2
		se.insert()
		self.assertRaises(SerialNoQtyError, se.submit)

	def test_serial_no_qty_less(self):
		se = frappe.copy_doc(test_records[0])
		se.get("mtn_details")[0].item_code = "_Test Serialized Item"
		se.get("mtn_details")[0].qty = 2
		se.get("mtn_details")[0].serial_no = "ABCD"
		se.get("mtn_details")[0].transfer_qty = 2
		se.insert()
		self.assertRaises(SerialNoQtyError, se.submit)

	def test_serial_no_transfer_in(self):
		self._clear_stock_account_balance()
		se = frappe.copy_doc(test_records[0])
		se.get("mtn_details")[0].item_code = "_Test Serialized Item"
		se.get("mtn_details")[0].qty = 2
		se.get("mtn_details")[0].serial_no = "ABCD\nEFGH"
		se.get("mtn_details")[0].transfer_qty = 2
		se.insert()
		se.submit()

		self.assertTrue(frappe.db.exists("Serial No", "ABCD"))
		self.assertTrue(frappe.db.exists("Serial No", "EFGH"))

		se.cancel()
		self.assertFalse(frappe.db.get_value("Serial No", "ABCD", "warehouse"))

	def test_serial_no_not_exists(self):
		self._clear_stock_account_balance()
		frappe.db.sql("delete from `tabSerial No` where name in ('ABCD', 'EFGH')")
		make_serialized_item(target_warehouse="_Test Warehouse 1 - _TC")
		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Issue"
		se.get("mtn_details")[0].item_code = "_Test Serialized Item With Series"
		se.get("mtn_details")[0].qty = 2
		se.get("mtn_details")[0].s_warehouse = "_Test Warehouse 1 - _TC"
		se.get("mtn_details")[0].t_warehouse = None
		se.get("mtn_details")[0].serial_no = "ABCD\nEFGH"
		se.get("mtn_details")[0].transfer_qty = 2
		se.insert()

		self.assertRaises(SerialNoNotExistsError, se.submit)

	def test_serial_duplicate(self):
		self._clear_stock_account_balance()
		se, serial_nos = self.test_serial_by_series()

		se = frappe.copy_doc(test_records[0])
		se.get("mtn_details")[0].item_code = "_Test Serialized Item With Series"
		se.get("mtn_details")[0].qty = 1
		se.get("mtn_details")[0].serial_no = serial_nos[0]
		se.get("mtn_details")[0].transfer_qty = 1
		se.insert()
		self.assertRaises(SerialNoDuplicateError, se.submit)

	def test_serial_by_series(self):
		self._clear_stock_account_balance()
		se = make_serialized_item()

		serial_nos = get_serial_nos(se.get("mtn_details")[0].serial_no)

		self.assertTrue(frappe.db.exists("Serial No", serial_nos[0]))
		self.assertTrue(frappe.db.exists("Serial No", serial_nos[1]))

		return se, serial_nos

	def test_serial_item_error(self):
		se, serial_nos = self.test_serial_by_series()
		make_serialized_item("_Test Serialized Item", "ABCD\nEFGH")

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Transfer"
		se.get("mtn_details")[0].item_code = "_Test Serialized Item"
		se.get("mtn_details")[0].qty = 1
		se.get("mtn_details")[0].transfer_qty = 1
		se.get("mtn_details")[0].serial_no = serial_nos[0]
		se.get("mtn_details")[0].s_warehouse = "_Test Warehouse - _TC"
		se.get("mtn_details")[0].t_warehouse = "_Test Warehouse 1 - _TC"
		se.insert()
		self.assertRaises(SerialNoItemError, se.submit)

	def test_serial_move(self):
		self._clear_stock_account_balance()
		se = make_serialized_item()
		serial_no = get_serial_nos(se.get("mtn_details")[0].serial_no)[0]

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Transfer"
		se.get("mtn_details")[0].item_code = "_Test Serialized Item With Series"
		se.get("mtn_details")[0].qty = 1
		se.get("mtn_details")[0].transfer_qty = 1
		se.get("mtn_details")[0].serial_no = serial_no
		se.get("mtn_details")[0].s_warehouse = "_Test Warehouse - _TC"
		se.get("mtn_details")[0].t_warehouse = "_Test Warehouse 1 - _TC"
		se.insert()
		se.submit()
		self.assertTrue(frappe.db.get_value("Serial No", serial_no, "warehouse"), "_Test Warehouse 1 - _TC")

		se.cancel()
		self.assertTrue(frappe.db.get_value("Serial No", serial_no, "warehouse"), "_Test Warehouse - _TC")

	def test_serial_warehouse_error(self):
		self._clear_stock_account_balance()
		make_serialized_item(target_warehouse="_Test Warehouse 1 - _TC")

		t = make_serialized_item()
		serial_nos = get_serial_nos(t.get("mtn_details")[0].serial_no)

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Transfer"
		se.get("mtn_details")[0].item_code = "_Test Serialized Item With Series"
		se.get("mtn_details")[0].qty = 1
		se.get("mtn_details")[0].transfer_qty = 1
		se.get("mtn_details")[0].serial_no = serial_nos[0]
		se.get("mtn_details")[0].s_warehouse = "_Test Warehouse 1 - _TC"
		se.get("mtn_details")[0].t_warehouse = "_Test Warehouse - _TC"
		se.insert()
		self.assertRaises(SerialNoWarehouseError, se.submit)

	def test_serial_cancel(self):
		self._clear_stock_account_balance()
		se, serial_nos = self.test_serial_by_series()
		se.cancel()

		serial_no = get_serial_nos(se.get("mtn_details")[0].serial_no)[0]
		self.assertFalse(frappe.db.get_value("Serial No", serial_no, "warehouse"))

	def test_warehouse_company_validation(self):
		set_perpetual_inventory(0)
		self._clear_stock_account_balance()
		frappe.get_doc("User", "test2@example.com")\
			.add_roles("Sales User", "Sales Manager", "Material User", "Material Manager")
		frappe.set_user("test2@example.com")

		from erpnext.stock.utils import InvalidWarehouseCompany
		st1 = frappe.copy_doc(test_records[0])
		st1.get("mtn_details")[0].t_warehouse="_Test Warehouse 2 - _TC1"
		st1.insert()
		self.assertRaises(InvalidWarehouseCompany, st1.submit)

	# permission tests
	def test_warehouse_user(self):
		set_perpetual_inventory(0)

		frappe.defaults.add_default("Warehouse", "_Test Warehouse 1 - _TC", "test@example.com", "User Permission")
		frappe.defaults.add_default("Warehouse", "_Test Warehouse 2 - _TC1", "test2@example.com", "User Permission")
		test_user = frappe.get_doc("User", "test@example.com")
		test_user.add_roles("Sales User", "Sales Manager", "Material User")
		test_user.remove_roles("Material Manager")

		frappe.get_doc("User", "test2@example.com")\
			.add_roles("Sales User", "Sales Manager", "Material User", "Material Manager")

		frappe.set_user("test@example.com")
		st1 = frappe.copy_doc(test_records[0])
		st1.company = "_Test Company 1"
		st1.get("mtn_details")[0].t_warehouse="_Test Warehouse 2 - _TC1"
		self.assertRaises(frappe.PermissionError, st1.insert)

		frappe.set_user("test2@example.com")
		st1 = frappe.copy_doc(test_records[0])
		st1.company = "_Test Company 1"
		st1.get("mtn_details")[0].t_warehouse="_Test Warehouse 2 - _TC1"
		st1.insert()
		st1.submit()

		frappe.defaults.clear_default("Warehouse", "_Test Warehouse 1 - _TC",
			"test@example.com", parenttype="User Permission")
		frappe.defaults.clear_default("Warehouse", "_Test Warehouse 2 - _TC1",
			"test2@example.com", parenttype="User Permission")

	def test_freeze_stocks(self):
		self._clear_stock_account_balance()
		frappe.db.set_value('Stock Settings', None,'stock_auth_role', '')

		# test freeze_stocks_upto
		date_newer_than_test_records = add_days(getdate(test_records[0]['posting_date']), 5)
		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto", date_newer_than_test_records)
		se = frappe.copy_doc(test_records[0]).insert()
		self.assertRaises (StockFreezeError, se.submit)
		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto", '')

		# test freeze_stocks_upto_days
		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto_days", 7)
		se = frappe.copy_doc(test_records[0]).insert()
		self.assertRaises (StockFreezeError, se.submit)
		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto_days", 0)

	def test_production_order(self):
		bom_no = frappe.db.get_value("BOM", {"item": "_Test FG Item 2",
			"is_default": 1, "docstatus": 1})

		production_order = frappe.new_doc("Production Order")
		production_order.update({
			"company": "_Test Company",
			"fg_warehouse": "_Test Warehouse 1 - _TC",
			"production_item": "_Test FG Item 2",
			"bom_no": bom_no,
			"qty": 1.0,
			"stock_uom": "Nos",
			"wip_warehouse": "_Test Warehouse - _TC"
		})
		production_order.insert()
		production_order.submit()

		self._insert_material_receipt()

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.update({
			"purpose": "Manufacture",
			"production_order": production_order.name,
			"bom_no": bom_no,
			"fg_completed_qty": "1",
			"total_fixed_cost": 1000
		})
		stock_entry.get_items()
		fg_rate = [d.amount for d in stock_entry.get("mtn_details") if d.item_code=="_Test FG Item 2"][0]
		self.assertEqual(fg_rate, 1200.00)
		fg_rate = [d.amount for d in stock_entry.get("mtn_details") if d.item_code=="_Test Item"][0]
		self.assertEqual(fg_rate, 100.00)

def make_serialized_item(item_code=None, serial_no=None, target_warehouse=None):
	se = frappe.copy_doc(test_records[0])
	se.get("mtn_details")[0].item_code = item_code or "_Test Serialized Item With Series"
	se.get("mtn_details")[0].serial_no = serial_no
	se.get("mtn_details")[0].qty = 2
	se.get("mtn_details")[0].transfer_qty = 2

	if target_warehouse:
		se.get("mtn_details")[0].t_warehouse = target_warehouse

	se.insert()
	se.submit()
	return se

def make_stock_entry(item, source, target, qty, incoming_rate=None):
	s = frappe.new_doc("Stock Entry")
	if source and target:
		s.purpose = "Material Transfer"
	elif source:
		s.purpose = "Material Issue"
	else:
		s.purpose = "Material Receipt"
	s.company = "_Test Company"
	s.append("mtn_details", {
		"item_code": item,
		"s_warehouse": source,
		"t_warehouse": target,
		"qty": qty,
		"incoming_rate": incoming_rate,
		"conversion_factor": 1.0
	})
	s.insert()
	s.submit()
	return s

test_records = frappe.get_test_records('Stock Entry')
