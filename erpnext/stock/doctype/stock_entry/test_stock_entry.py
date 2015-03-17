# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, unittest
import frappe.defaults
from frappe.utils import flt, nowdate, nowtime
from erpnext.stock.doctype.serial_no.serial_no import *
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt \
	import set_perpetual_inventory, make_purchase_receipt
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import StockFreezeError
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order, create_dn_against_so
from erpnext.stock.doctype.stock_entry.stock_entry import make_return_jv, NotUpdateStockError
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import create_stock_reconciliation

def get_sle(**args):
	condition, values = "", []
	for key, value in args.iteritems():
		condition += " and " if condition else " where "
		condition += "`{0}`=%s".format(key)
		values.append(value)

	return frappe.db.sql("""select * from `tabStock Ledger Entry` %s
		order by timestamp(posting_date, posting_time) desc, name desc limit 1"""% condition,
		values, as_dict=1)

class TestStockEntry(unittest.TestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		set_perpetual_inventory(0)

	def test_fifo(self):
		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)
		item_code = "_Test Item 2"
		warehouse = "_Test Warehouse - _TC"
		
		create_stock_reconciliation(item_code="_Test Item 2", warehouse="_Test Warehouse - _TC", 
			qty=0, rate=100)

		make_stock_entry(item_code=item_code, target=warehouse, qty=1, incoming_rate=10)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]
		self.assertEqual([[1, 10]], eval(sle.stock_queue))

		# negative qty
		make_stock_entry(item_code=item_code, source=warehouse, qty=2, incoming_rate=10)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]

		self.assertEqual([[-1, 10]], eval(sle.stock_queue))

		# further negative
		make_stock_entry(item_code=item_code, source=warehouse, qty=1)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]

		self.assertEqual([[-2, 10]], eval(sle.stock_queue))

		# move stock to positive
		make_stock_entry(item_code=item_code, target=warehouse, qty=3, incoming_rate=20)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]
		self.assertEqual([[1, 20]], eval(sle.stock_queue))		
		
		# incoming entry with diff rate
		make_stock_entry(item_code=item_code, target=warehouse, qty=1, incoming_rate=30)
		sle = get_sle(item_code = item_code, warehouse = warehouse)[0]

		self.assertEqual([[1, 20],[1, 30]], eval(sle.stock_queue))

		frappe.db.set_default("allow_negative_stock", 0)		

	def test_auto_material_request(self):
		self._test_auto_material_request("_Test Item")

	def test_auto_material_request_for_variant(self):
		self._test_auto_material_request("_Test Variant Item-S")

	def _test_auto_material_request(self, item_code):
		item = frappe.get_doc("Item", item_code)

		if item.variant_of:
			template = frappe.get_doc("Item", item.variant_of)
		else:
			template = item

		# stock entry reqd for auto-reorder
		create_stock_reconciliation(item_code=item_code, warehouse="_Test Warehouse - _TC", 
			qty=10, rate=100)

		frappe.db.set_value("Stock Settings", None, "auto_indent", 1)
		projected_qty = frappe.db.get_value("Bin", {"item_code": item_code,
			"warehouse": "_Test Warehouse - _TC"}, "projected_qty") or 0

		# update re-level qty so that it is more than projected_qty
		if projected_qty > template.reorder_levels[0].warehouse_reorder_level:
			template.reorder_levels[0].warehouse_reorder_level += projected_qty
			template.save()

		from erpnext.stock.reorder_item import reorder_item
		mr_list = reorder_item()

		frappe.db.set_value("Stock Settings", None, "auto_indent", 0)

		items = []
		for mr in mr_list:
			for d in mr.items:
				items.append(d.item_code)

		self.assertTrue(item_code in items)

	def test_material_receipt_gl_entry(self):
		set_perpetual_inventory()
		
		mr = make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", 
			qty=50, incoming_rate=100)

		stock_in_hand_account = frappe.db.get_value("Account", {"account_type": "Warehouse",
			"warehouse": mr.get("items")[0].t_warehouse})

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
		set_perpetual_inventory()

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", 
			qty=50, incoming_rate=100)
		
		mi = make_stock_entry(item_code="_Test Item", source="_Test Warehouse - _TC", qty=40)

		self.check_stock_ledger_entries("Stock Entry", mi.name,
			[["_Test Item", "_Test Warehouse - _TC", -40.0]])

		stock_in_hand_account = frappe.db.get_value("Account", {"account_type": "Warehouse",
			"warehouse": "_Test Warehouse - _TC"})
			
		stock_value_diff = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Stock Entry", 
			"voucher_no": mi.name}, "stock_value_difference"))

		self.check_gl_entries("Stock Entry", mi.name,
			sorted([
				[stock_in_hand_account, 0.0, stock_value_diff],
				["Stock Adjustment - _TC", stock_value_diff, 0.0]
			])
		)

		mi.cancel()
		
		self.assertFalse(frappe.db.sql("""select name from `tabStock Ledger Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mi.name))

		self.assertFalse(frappe.db.sql("""select name from `tabGL Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mi.name))

	def test_material_transfer_gl_entry(self):
		set_perpetual_inventory()
		
		create_stock_reconciliation(qty=100, rate=100)
			
		mtn = make_stock_entry(item_code="_Test Item", source="_Test Warehouse - _TC", 
			target="_Test Warehouse 1 - _TC", qty=45)
			
		self.check_stock_ledger_entries("Stock Entry", mtn.name,
			[["_Test Item", "_Test Warehouse - _TC", -45.0], ["_Test Item", "_Test Warehouse 1 - _TC", 45.0]])

		stock_in_hand_account = frappe.db.get_value("Account", {"account_type": "Warehouse",
			"warehouse": mtn.get("items")[0].s_warehouse})

		fixed_asset_account = frappe.db.get_value("Account", {"account_type": "Warehouse",
			"warehouse": mtn.get("items")[0].t_warehouse})

		stock_value_diff = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Stock Entry", 
			"voucher_no": mtn.name, "warehouse": "_Test Warehouse - _TC"}, "stock_value_difference"))

		self.check_gl_entries("Stock Entry", mtn.name,
			sorted([
				[stock_in_hand_account, 0.0, stock_value_diff],
				[fixed_asset_account, stock_value_diff, 0.0],
			])
		)
		
		mtn.cancel()
		self.assertFalse(frappe.db.sql("""select * from `tabStock Ledger Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mtn.name))

		self.assertFalse(frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type='Stock Entry' and voucher_no=%s""", mtn.name))

	def test_repack_no_change_in_valuation(self):
		set_perpetual_inventory(0)

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, incoming_rate=100)
		make_stock_entry(item_code="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", 
			qty=50, incoming_rate=100)

		repack = frappe.copy_doc(test_records[3])
		repack.posting_date = nowdate()
		repack.posting_time = nowtime()
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
		set_perpetual_inventory()

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, incoming_rate=100)
		
		repack = frappe.copy_doc(test_records[3])
		repack.posting_date = nowdate()
		repack.posting_time = nowtime()
		repack.additional_operating_cost = 1000.0
		repack.insert()
		repack.submit()

		stock_in_hand_account = frappe.db.get_value("Account", {"account_type": "Warehouse",
			"warehouse": repack.get("items")[1].t_warehouse})
			
		rm_stock_value_diff = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Stock Entry", 
			"voucher_no": repack.name, "item_code": "_Test Item"}, "stock_value_difference"))
		
		fg_stock_value_diff = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Stock Entry", 
			"voucher_no": repack.name, "item_code": "_Test Item Home Desktop 100"}, "stock_value_difference"))
		
		stock_value_diff = flt(fg_stock_value_diff - rm_stock_value_diff, 2)

		self.check_gl_entries("Stock Entry", repack.name,
			sorted([
				[stock_in_hand_account, stock_value_diff, 0.0],
				["Stock Adjustment - _TC", 0.0, stock_value_diff],
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

	def _test_sales_invoice_return(self, item_code, delivered_qty, returned_qty):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		si = create_sales_invoice(item_code=item_code, qty=delivered_qty)

		se = make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=returned_qty, 
			purpose="Sales Return", sales_invoice_no=si.name, do_not_save=True)
		self.assertRaises(NotUpdateStockError, se.insert)

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=200, incoming_rate=100)

		# check currency available qty in bin
		actual_qty_0 = get_qty_after_transaction()

		# insert a pos invoice with update stock
		si = create_sales_invoice(update_stock=1, item_code=item_code, qty=5)

		# check available bin qty after invoice submission
		actual_qty_1 = get_qty_after_transaction()

		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)

		# check if item is validated
		se = make_stock_entry(item_code="_Test Item Home Desktop 200", target="_Test Warehouse - _TC", 
			qty=returned_qty, purpose="Sales Return", sales_invoice_no=si.name, do_not_save=True)

		self.assertRaises(frappe.DoesNotExistError, se.insert)

		# try again
		se = make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", 
			qty=returned_qty, purpose="Sales Return", sales_invoice_no=si.name)

		# check if available qty is increased
		actual_qty_2 = get_qty_after_transaction()

		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)

		return se

	def test_sales_invoice_return_of_non_packing_item(self):
		self._test_sales_invoice_return("_Test Item", 5, 2)

	def test_sales_invoice_return_of_packing_item(self):
		self._test_sales_invoice_return("_Test Sales BOM Item", 25, 20)

	def _test_delivery_note_return(self, item_code, delivered_qty, returned_qty):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		
		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, incoming_rate=100)

		actual_qty_0 = get_qty_after_transaction()
		# make a delivery note based on this invoice
		dn = create_delivery_note(item_code="_Test Item", 
			warehouse="_Test Warehouse - _TC", qty=delivered_qty)

		actual_qty_1 = get_qty_after_transaction()

		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)

		si = make_sales_invoice(dn.name)
		si.insert()
		si.submit()

		# insert and submit stock entry for sales return
		se = make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", 
			qty=returned_qty, purpose="Sales Return", delivery_note_no=dn.name)

		actual_qty_2 = get_qty_after_transaction()
		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)

		return se

	def test_delivery_note_return_of_non_packing_item(self):
		self._test_delivery_note_return("_Test Item", 5, 2)

	def test_delivery_note_return_of_packing_item(self):
		self._test_delivery_note_return("_Test Sales BOM Item", 25, 20)

	def _test_sales_return_jv(self, se):
		jv = make_return_jv(se.name)

		self.assertEqual(len(jv.get("accounts")), 2)
		self.assertEqual(jv.get("voucher_type"), "Credit Note")
		self.assertEqual(jv.get("posting_date"), se.posting_date)
		self.assertEqual(jv.get("accounts")[0].get("account"), "Debtors - _TC")
		self.assertEqual(jv.get("accounts")[0].get("party_type"), "Customer")
		self.assertEqual(jv.get("accounts")[0].get("party"), "_Test Customer")
		self.assertTrue(jv.get("accounts")[0].get("against_invoice"))
		self.assertEqual(jv.get("accounts")[1].get("account"), "Sales - _TC")

	def test_make_return_jv_for_sales_invoice_non_packing_item(self):
		se = self._test_sales_invoice_return("_Test Item", 5, 2)
		self._test_sales_return_jv(se)

	def test_make_return_jv_for_sales_invoice_packing_item(self):
		se = self._test_sales_invoice_return("_Test Sales BOM Item", 25, 20)
		self._test_sales_return_jv(se)

	def test_make_return_jv_for_delivery_note_non_packing_item(self):
		se = self._test_delivery_note_return("_Test Item", 5, 2)
		self._test_sales_return_jv(se)

		se = self._test_delivery_note_return_against_sales_order("_Test Item", 5, 2)
		self._test_sales_return_jv(se)

	def test_make_return_jv_for_delivery_note_packing_item(self):
		se = self._test_delivery_note_return("_Test Sales BOM Item", 25, 20)
		self._test_sales_return_jv(se)

		se = self._test_delivery_note_return_against_sales_order("_Test Sales BOM Item", 25, 20)
		self._test_sales_return_jv(se)

	def _test_delivery_note_return_against_sales_order(self, item_code, delivered_qty, returned_qty):
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
		
		actual_qty_0 = get_qty_after_transaction()
		
		so = make_sales_order(qty=50)

		dn = create_dn_against_so(so.name, delivered_qty)
		
		actual_qty_1 = get_qty_after_transaction()
		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)

		si = make_sales_invoice(so.name)
		si.insert()
		si.submit()

		# insert and submit stock entry for sales return
		se = make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", 
			qty=returned_qty, purpose="Sales Return", delivery_note_no=dn.name)

		actual_qty_2 = get_qty_after_transaction()
		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)

		return se

	def test_purchase_receipt_return(self):
		actual_qty_0 = get_qty_after_transaction()

		# submit purchase receipt
		pr = make_purchase_receipt(item_code="_Test Item", warehouse="_Test Warehouse - _TC", qty=5)

		actual_qty_1 = get_qty_after_transaction()

		self.assertEquals(actual_qty_0 + 5, actual_qty_1)

		pi_doc = make_purchase_invoice(pr.name)

		pi = frappe.get_doc(pi_doc)
		pi.posting_date = pr.posting_date
		pi.credit_to = "_Test Payable - _TC"
		for d in pi.get("items"):
			d.expense_account = "_Test Account Cost for Goods Sold - _TC"
			d.cost_center = "_Test Cost Center - _TC"

		for d in pi.get("taxes"):
			d.cost_center = "_Test Cost Center - _TC"

		pi.insert()
		pi.submit()

		# submit purchase return
		se = make_stock_entry(item_code="_Test Item", source="_Test Warehouse - _TC", 
			qty=5, purpose="Purchase Return", purchase_receipt_no=pr.name)

		actual_qty_2 = get_qty_after_transaction()

		self.assertEquals(actual_qty_1 - 5, actual_qty_2)

		return se, pr.name

	def test_over_stock_return(self):
		from erpnext.stock.doctype.stock_entry.stock_entry import StockOverReturnError

		# out of 10, 5 gets returned
		prev_se, pr_docname = self.test_purchase_receipt_return()

		se = make_stock_entry(item_code="_Test Item", source="_Test Warehouse - _TC", 
			qty=6, purpose="Purchase Return", purchase_receipt_no=pr_docname, do_not_save=True)
		
		self.assertRaises(StockOverReturnError, se.insert)

	def _test_purchase_return_jv(self, se):
		jv = make_return_jv(se.name)

		self.assertEqual(len(jv.get("accounts")), 2)
		self.assertEqual(jv.get("voucher_type"), "Debit Note")
		self.assertEqual(jv.get("posting_date"), se.posting_date)
		self.assertEqual(jv.get("accounts")[0].get("account"), "_Test Payable - _TC")
		self.assertEqual(jv.get("accounts")[0].get("party"), "_Test Supplier")
		self.assertEqual(jv.get("accounts")[1].get("account"), "_Test Account Cost for Goods Sold - _TC")
		self.assertTrue(jv.get("accounts")[0].get("against_voucher"))

	def test_make_return_jv_for_purchase_receipt(self):
		se, pr_name = self.test_purchase_receipt_return()
		self._test_purchase_return_jv(se)

		se, pr_name = self._test_purchase_return_return_against_purchase_order()
		self._test_purchase_return_jv(se)

	def _test_purchase_return_return_against_purchase_order(self):

		actual_qty_0 = get_qty_after_transaction()

		from erpnext.buying.doctype.purchase_order.test_purchase_order \
			import test_records as purchase_order_test_records

		from erpnext.buying.doctype.purchase_order.purchase_order import \
			make_purchase_receipt, make_purchase_invoice

		# submit purchase receipt
		po = frappe.copy_doc(purchase_order_test_records[0])
		po.transaction_date = nowdate()
		po.is_subcontracted = None
		po.get("items")[0].item_code = "_Test Item"
		po.get("items")[0].rate = 50
		po.insert()
		po.submit()

		pr_doc = make_purchase_receipt(po.name)

		pr = frappe.get_doc(pr_doc)
		pr.posting_date = po.transaction_date
		pr.insert()
		pr.submit()

		actual_qty_1 = get_qty_after_transaction()

		self.assertEquals(actual_qty_0 + 10, actual_qty_1)

		pi_doc = make_purchase_invoice(po.name)

		pi = frappe.get_doc(pi_doc)
		pi.posting_date = pr.posting_date
		pi.credit_to = "_Test Payable - _TC"
		for d in pi.get("items"):
			d.expense_account = "_Test Account Cost for Goods Sold - _TC"
			d.cost_center = "_Test Cost Center - _TC"
		for d in pi.get("taxes"):
			d.cost_center = "_Test Cost Center - _TC"

		pi.run_method("calculate_taxes_and_totals")
		pi.bill_no = "NA"
		pi.insert()
		pi.submit()

		# submit purchase return
		se = make_stock_entry(item_code="_Test Item", source="_Test Warehouse - _TC", 
			qty=5, purpose="Purchase Return", purchase_receipt_no=pr.name)

		actual_qty_2 = get_qty_after_transaction()

		self.assertEquals(actual_qty_1 - 5, actual_qty_2)

		return se, pr.name

	def test_serial_no_not_reqd(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].serial_no = "ABCD"
		se.insert()
		self.assertRaises(SerialNoNotRequiredError, se.submit)

	def test_serial_no_reqd(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].transfer_qty = 2
		se.insert()
		self.assertRaises(SerialNoRequiredError, se.submit)

	def test_serial_no_qty_more(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].serial_no = "ABCD\nEFGH\nXYZ"
		se.get("items")[0].transfer_qty = 2
		se.insert()
		self.assertRaises(SerialNoQtyError, se.submit)

	def test_serial_no_qty_less(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].serial_no = "ABCD"
		se.get("items")[0].transfer_qty = 2
		se.insert()
		self.assertRaises(SerialNoQtyError, se.submit)

	def test_serial_no_transfer_in(self):
		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 2
		se.get("items")[0].serial_no = "ABCD\nEFGH"
		se.get("items")[0].transfer_qty = 2
		se.insert()
		se.submit()

		self.assertTrue(frappe.db.exists("Serial No", "ABCD"))
		self.assertTrue(frappe.db.exists("Serial No", "EFGH"))

		se.cancel()
		self.assertFalse(frappe.db.get_value("Serial No", "ABCD", "warehouse"))

	def test_serial_no_not_exists(self):
		frappe.db.sql("delete from `tabSerial No` where name in ('ABCD', 'EFGH')")
		make_serialized_item(target_warehouse="_Test Warehouse 1 - _TC")
		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Issue"
		se.get("items")[0].item_code = "_Test Serialized Item With Series"
		se.get("items")[0].qty = 2
		se.get("items")[0].s_warehouse = "_Test Warehouse 1 - _TC"
		se.get("items")[0].t_warehouse = None
		se.get("items")[0].serial_no = "ABCD\nEFGH"
		se.get("items")[0].transfer_qty = 2
		se.insert()

		self.assertRaises(SerialNoNotExistsError, se.submit)

	def test_serial_duplicate(self):
		se, serial_nos = self.test_serial_by_series()

		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = "_Test Serialized Item With Series"
		se.get("items")[0].qty = 1
		se.get("items")[0].serial_no = serial_nos[0]
		se.get("items")[0].transfer_qty = 1
		se.insert()
		self.assertRaises(SerialNoDuplicateError, se.submit)

	def test_serial_by_series(self):
		se = make_serialized_item()

		serial_nos = get_serial_nos(se.get("items")[0].serial_no)

		self.assertTrue(frappe.db.exists("Serial No", serial_nos[0]))
		self.assertTrue(frappe.db.exists("Serial No", serial_nos[1]))

		return se, serial_nos

	def test_serial_item_error(self):
		se, serial_nos = self.test_serial_by_series()
		make_serialized_item("_Test Serialized Item", "ABCD\nEFGH")

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Transfer"
		se.get("items")[0].item_code = "_Test Serialized Item"
		se.get("items")[0].qty = 1
		se.get("items")[0].transfer_qty = 1
		se.get("items")[0].serial_no = serial_nos[0]
		se.get("items")[0].s_warehouse = "_Test Warehouse - _TC"
		se.get("items")[0].t_warehouse = "_Test Warehouse 1 - _TC"
		se.insert()
		self.assertRaises(SerialNoItemError, se.submit)

	def test_serial_move(self):
		se = make_serialized_item()
		serial_no = get_serial_nos(se.get("items")[0].serial_no)[0]

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Transfer"
		se.get("items")[0].item_code = "_Test Serialized Item With Series"
		se.get("items")[0].qty = 1
		se.get("items")[0].transfer_qty = 1
		se.get("items")[0].serial_no = serial_no
		se.get("items")[0].s_warehouse = "_Test Warehouse - _TC"
		se.get("items")[0].t_warehouse = "_Test Warehouse 1 - _TC"
		se.insert()
		se.submit()
		self.assertTrue(frappe.db.get_value("Serial No", serial_no, "warehouse"), "_Test Warehouse 1 - _TC")

		se.cancel()
		self.assertTrue(frappe.db.get_value("Serial No", serial_no, "warehouse"), "_Test Warehouse - _TC")

	def test_serial_warehouse_error(self):
		make_serialized_item(target_warehouse="_Test Warehouse 1 - _TC")

		t = make_serialized_item()
		serial_nos = get_serial_nos(t.get("items")[0].serial_no)

		se = frappe.copy_doc(test_records[0])
		se.purpose = "Material Transfer"
		se.get("items")[0].item_code = "_Test Serialized Item With Series"
		se.get("items")[0].qty = 1
		se.get("items")[0].transfer_qty = 1
		se.get("items")[0].serial_no = serial_nos[0]
		se.get("items")[0].s_warehouse = "_Test Warehouse 1 - _TC"
		se.get("items")[0].t_warehouse = "_Test Warehouse - _TC"
		se.insert()
		self.assertRaises(SerialNoWarehouseError, se.submit)

	def test_serial_cancel(self):
		se, serial_nos = self.test_serial_by_series()
		se.cancel()

		serial_no = get_serial_nos(se.get("items")[0].serial_no)[0]
		self.assertFalse(frappe.db.get_value("Serial No", serial_no, "warehouse"))

	def test_warehouse_company_validation(self):
		set_perpetual_inventory(0)
		frappe.get_doc("User", "test2@example.com")\
			.add_roles("Sales User", "Sales Manager", "Material User", "Material Manager")
		frappe.set_user("test2@example.com")

		from erpnext.stock.utils import InvalidWarehouseCompany
		st1 = frappe.copy_doc(test_records[0])
		st1.get("items")[0].t_warehouse="_Test Warehouse 2 - _TC1"
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
		st1.get("items")[0].t_warehouse="_Test Warehouse 2 - _TC1"
		self.assertRaises(frappe.PermissionError, st1.insert)

		frappe.set_user("test2@example.com")
		st1 = frappe.copy_doc(test_records[0])
		st1.company = "_Test Company 1"
		st1.get("items")[0].t_warehouse="_Test Warehouse 2 - _TC1"
		st1.insert()
		st1.submit()

		frappe.defaults.clear_default("Warehouse", "_Test Warehouse 1 - _TC",
			"test@example.com", parenttype="User Permission")
		frappe.defaults.clear_default("Warehouse", "_Test Warehouse 2 - _TC1",
			"test2@example.com", parenttype="User Permission")

	def test_freeze_stocks(self):
		frappe.db.set_value('Stock Settings', None,'stock_auth_role', '')

		# test freeze_stocks_upto
		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto", add_days(nowdate(), 5))
		se = frappe.copy_doc(test_records[0]).insert()
		self.assertRaises(StockFreezeError, se.submit)

		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto", '')

		# test freeze_stocks_upto_days
		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto_days", 7)
		se = frappe.copy_doc(test_records[0])
		se.posting_date = add_days(nowdate(), -15)
		se.insert()
		self.assertRaises(StockFreezeError, se.submit)
		frappe.db.set_value("Stock Settings", None, "stock_frozen_upto_days", 0)

	def test_production_order(self):
		bom_no, bom_operation_cost = frappe.db.get_value("BOM", {"item": "_Test FG Item 2",
			"is_default": 1, "docstatus": 1}, ["name", "operating_cost"])

		production_order = frappe.new_doc("Production Order")
		production_order.update({
			"company": "_Test Company",
			"fg_warehouse": "_Test Warehouse 1 - _TC",
			"production_item": "_Test FG Item 2",
			"bom_no": bom_no,
			"qty": 1.0,
			"stock_uom": "_Test UOM",
			"wip_warehouse": "_Test Warehouse - _TC"
		})
		production_order.insert()
		production_order.submit()

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, incoming_rate=100)

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.update({
			"purpose": "Manufacture",
			"production_order": production_order.name,
			"bom_no": bom_no,
			"fg_completed_qty": "1",
			"additional_operating_cost": 1000
		})
		stock_entry.get_items()

		rm_cost = 0
		for d in stock_entry.get("items"):
			if d.s_warehouse:
				rm_cost += flt(d.amount)
								
		fg_cost = filter(lambda x: x.item_code=="_Test FG Item 2", stock_entry.get("items"))[0].amount
		
		self.assertEqual(fg_cost, rm_cost + bom_operation_cost + stock_entry.additional_operating_cost)
		

	def test_variant_production_order(self):
		bom_no = frappe.db.get_value("BOM", {"item": "_Test Variant Item",
			"is_default": 1, "docstatus": 1})

		production_order = frappe.new_doc("Production Order")
		production_order.update({
			"company": "_Test Company",
			"fg_warehouse": "_Test Warehouse 1 - _TC",
			"production_item": "_Test Variant Item-S",
			"bom_no": bom_no,
			"qty": 1.0,
			"stock_uom": "_Test UOM",
			"wip_warehouse": "_Test Warehouse - _TC"
		})
		production_order.insert()
		production_order.submit()

		from erpnext.manufacturing.doctype.production_order.production_order import make_stock_entry

		stock_entry = frappe.get_doc(make_stock_entry(production_order.name, "Manufacture", 1))
		stock_entry.insert()
		self.assertTrue("_Test Variant Item-S" in [d.item_code for d in stock_entry.items])

def make_serialized_item(item_code=None, serial_no=None, target_warehouse=None):
	se = frappe.copy_doc(test_records[0])
	se.get("items")[0].item_code = item_code or "_Test Serialized Item With Series"
	se.get("items")[0].serial_no = serial_no
	se.get("items")[0].qty = 2
	se.get("items")[0].transfer_qty = 2

	if target_warehouse:
		se.get("items")[0].t_warehouse = target_warehouse

	se.insert()
	se.submit()
	return se

def make_stock_entry(**args):
	from erpnext.accounts.utils import get_fiscal_year
	
	s = frappe.new_doc("Stock Entry")
	args = frappe._dict(args)
	if args.posting_date:
		s.posting_date = args.posting_date
	if args.posting_time:
		s.posting_time = args.posting_time
	
	if not args.purpose:
		if args.source and args.target:
			s.purpose = "Material Transfer"
		elif args.source:
			s.purpose = "Material Issue"
		else:
			s.purpose = "Material Receipt"
	else:
		s.purpose = args.purpose
		
	s.company = args.company or "_Test Company"
	s.fiscal_year = get_fiscal_year(s.posting_date)[0]
	s.purchase_receipt_no = args.purchase_receipt_no
	s.delivery_note_no = args.delivery_note_no
	s.sales_invoice_no = args.sales_invoice_no
	s.difference_account = args.difference_account or "Stock Adjustment - _TC"
	
	s.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"s_warehouse": args.from_warehouse or args.source,
		"t_warehouse": args.to_warehouse or args.target,
		"qty": args.qty,
		"incoming_rate": args.incoming_rate,
		"expense_account": args.expense_account or "Stock Adjustment - _TC",
		"conversion_factor": 1.0,
		"cost_center": "_Test Cost Center - _TC"
	})
	
	if not args.do_not_save:
		s.insert()
		if not args.do_not_submit:
			s.submit()
	return s
	
def get_qty_after_transaction(**args):
	args = frappe._dict(args)
	
	last_sle = get_previous_sle({
		"item_code": args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"posting_date": args.posting_date or nowdate(),
		"posting_time": args.posting_time or nowtime()
	})
	
	return flt(last_sle.get("qty_after_transaction"))

test_records = frappe.get_test_records('Stock Entry')
