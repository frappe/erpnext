# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes, unittest
from webnotes.utils import flt

class TestStockEntry(unittest.TestCase):
	def test_auto_material_request(self):
		webnotes.conn.sql("""delete from `tabMaterial Request Item`""")
		webnotes.conn.sql("""delete from `tabMaterial Request`""")
		self._clear_stock()
		
		webnotes.conn.set_value("Global Defaults", None, "auto_indent", True)

		st1 = webnotes.bean(copy=test_records[0])
		st1.insert()
		st1.submit()

		st2 = webnotes.bean(copy=test_records[1])
		st2.insert()
		st2.submit()
		
		from stock.utils import reorder_item
		reorder_item()
		
		mr_name = webnotes.conn.sql("""select parent from `tabMaterial Request Item`
			where item_code='_Test Item'""")
			
		self.assertTrue(mr_name)
		
		webnotes.conn.set_default("company", self.old_default_company)

	def test_warehouse_company_validation(self):
		from stock.doctype.stock_ledger_entry.stock_ledger_entry import InvalidWarehouseCompany
		st1 = webnotes.bean(copy=test_records[0])
		st1.doclist[1].t_warehouse="_Test Warehouse 2"
		st1.insert()
		self.assertRaises(InvalidWarehouseCompany, st1.submit)

	def test_material_receipt_gl_entry(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		
		mr = webnotes.bean(copy=test_records[0])
		mr.insert()
		mr.submit()
		
		stock_in_hand_account = webnotes.conn.get_value("Company", "_Test Company", 
			"stock_in_hand_account")
		
		self.check_stock_ledger_entries("Stock Entry", mr.doc.name, 
			[["_Test Item", "_Test Warehouse", 50.0]])
			
		self.check_gl_entries("Stock Entry", mr.doc.name, 
			sorted([
				[stock_in_hand_account, 5000.0, 0.0], 
				["Stock Adjustment - _TC", 0.0, 5000.0]
			])
		)
		
		mr.cancel()
		self.check_stock_ledger_entries("Stock Entry", mr.doc.name, 
			sorted([["_Test Item", "_Test Warehouse", 50.0], 
				["_Test Item", "_Test Warehouse", -50.0]]))
			
		self.check_gl_entries("Stock Entry", mr.doc.name, 
			sorted([
				[stock_in_hand_account, 5000.0, 0.0], 
				["Stock Adjustment - _TC", 0.0, 5000.0],
				[stock_in_hand_account, 0.0, 5000.0], 
				["Stock Adjustment - _TC", 5000.0, 0.0]
			])
		)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)

	def test_material_issue_gl_entry(self):
		self._clear_stock()
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		
		mr = webnotes.bean(copy=test_records[0])
		mr.insert()
		mr.submit()
		
		mi = webnotes.bean(copy=test_records[1])
		mi.insert()
		mi.submit()
		
		stock_in_hand_account = webnotes.conn.get_value("Company", "_Test Company", 
			"stock_in_hand_account")
		
		self.check_stock_ledger_entries("Stock Entry", mi.doc.name, 
			[["_Test Item", "_Test Warehouse", -40.0]])
			
		self.check_gl_entries("Stock Entry", mi.doc.name, 
			sorted([
				[stock_in_hand_account, 0.0, 4000.0], 
				["Stock Adjustment - _TC", 4000.0, 0.0]
			])
		)
		
		mi.cancel()
		
		self.check_stock_ledger_entries("Stock Entry", mi.doc.name, 
			sorted([["_Test Item", "_Test Warehouse", -40.0], 
				["_Test Item", "_Test Warehouse", 40.0]]))
			
		self.check_gl_entries("Stock Entry", mi.doc.name, 
			sorted([
				[stock_in_hand_account, 0.0, 4000.0], 
				["Stock Adjustment - _TC", 4000.0, 0.0],
				[stock_in_hand_account, 4000.0, 0.0], 
				["Stock Adjustment - _TC", 0.0, 4000.0],
			])
		)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
		webnotes.conn.set_default("company", self.old_default_company)
		
	def test_material_transfer_gl_entry(self):
		self._clear_stock()
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)

		mr = webnotes.bean(copy=test_records[0])
		mr.insert()
		mr.submit()

		mtn = webnotes.bean(copy=test_records[2])
		mtn.insert()
		mtn.submit()

		self.check_stock_ledger_entries("Stock Entry", mtn.doc.name, 
			[["_Test Item", "_Test Warehouse", -45.0], ["_Test Item", "_Test Warehouse 1", 45.0]])

		# no gl entry
		gl_entries = webnotes.conn.sql("""select * from `tabGL Entry` 
			where voucher_type = 'Stock Entry' and voucher_no=%s""", mtn.doc.name)
		self.assertFalse(gl_entries)
		
		mtn.cancel()
		self.check_stock_ledger_entries("Stock Entry", mtn.doc.name, 
			sorted([["_Test Item", "_Test Warehouse", 45.0], 
				["_Test Item", "_Test Warehouse 1", -45.0],
				["_Test Item", "_Test Warehouse", -45.0], 
				["_Test Item", "_Test Warehouse 1", 45.0]]))

		# no gl entry
		gl_entries = webnotes.conn.sql("""select * from `tabGL Entry` 
			where voucher_type = 'Stock Entry' and voucher_no=%s""", mtn.doc.name)
		self.assertFalse(gl_entries)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
		webnotes.conn.set_default("company", self.old_default_company)
	
	def check_stock_ledger_entries(self, voucher_type, voucher_no, expected_sle):
		# check stock ledger entries
		sle = webnotes.conn.sql("""select * from `tabStock Ledger Entry` where voucher_type = %s 
			and voucher_no = %s order by item_code, warehouse, actual_qty""", 
			(voucher_type, voucher_no), as_dict=1)
		self.assertTrue(sle)
		
		for i, sle in enumerate(sle):
			self.assertEquals(expected_sle[i][0], sle.item_code)
			self.assertEquals(expected_sle[i][1], sle.warehouse)
			self.assertEquals(expected_sle[i][2], sle.actual_qty)
		
	def check_gl_entries(self, voucher_type, voucher_no, expected_gl_entries):
		# check gl entries
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type=%s and voucher_no=%s 
			order by account asc, debit asc""", (voucher_type, voucher_no), as_dict=1)
		self.assertTrue(gl_entries)
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_gl_entries[i][0], gle.account)
			self.assertEquals(expected_gl_entries[i][1], gle.debit)
			self.assertEquals(expected_gl_entries[i][2], gle.credit)
	
	def _clear_stock(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.conn.sql("""delete from `tabBin`""")
		
		self.old_default_company = webnotes.conn.get_default("company")
		webnotes.conn.set_default("company", "_Test Company")
	
	def _insert_material_receipt(self):
		self._clear_stock()
		se1 = webnotes.bean(copy=test_records[0])
		se1.insert()
		se1.submit()
		
		se2 = webnotes.bean(copy=test_records[0])
		se2.doclist[1].item_code = "_Test Item Home Desktop 100"
		se2.insert()
		se2.submit()
		
		webnotes.conn.set_default("company", self.old_default_company)
		
	def _get_actual_qty(self):
		return flt(webnotes.conn.get_value("Bin", {"item_code": "_Test Item", 
			"warehouse": "_Test Warehouse"}, "actual_qty"))
			
	def _test_sales_invoice_return(self, item_code, delivered_qty, returned_qty):
		from stock.doctype.stock_entry.stock_entry import NotUpdateStockError
		
		from accounts.doctype.sales_invoice.test_sales_invoice \
			import test_records as sales_invoice_test_records
		
		# invalid sales invoice as update stock not checked
		si = webnotes.bean(copy=sales_invoice_test_records[1])
		si.insert()
		si.submit()
		
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Sales Return"
		se.doc.sales_invoice_no = si.doc.name
		se.doclist[1].qty = returned_qty
		se.doclist[1].transfer_qty = returned_qty
		self.assertRaises(NotUpdateStockError, se.insert)
		
		self._insert_material_receipt()
		
		# check currency available qty in bin
		actual_qty_0 = self._get_actual_qty()
		
		# insert a pos invoice with update stock
		si = webnotes.bean(copy=sales_invoice_test_records[1])
		si.doc.is_pos = si.doc.update_stock = 1
		si.doclist[1].warehouse = "_Test Warehouse"
		si.doclist[1].item_code = item_code
		si.insert()
		si.submit()
		
		# check available bin qty after invoice submission
		actual_qty_1 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)
		
		# check if item is validated
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Sales Return"
		se.doc.sales_invoice_no = si.doc.name
		se.doc.posting_date = "2013-03-10"
		se.doc.fiscal_year = "_Test Fiscal Year 2013"
		se.doclist[1].item_code = "_Test Item Home Desktop 200"
		se.doclist[1].qty = returned_qty
		se.doclist[1].transfer_qty = returned_qty
		
		# check if stock entry gets submitted
		self.assertRaises(webnotes.DoesNotExistError, se.insert)
		
		# try again
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Sales Return"
		se.doc.posting_date = "2013-03-10"
		se.doc.fiscal_year = "_Test Fiscal Year 2013"
		se.doc.sales_invoice_no = si.doc.name
		se.doclist[1].qty = returned_qty
		se.doclist[1].transfer_qty = returned_qty
		# in both cases item code remains _Test Item when returning
		se.insert()
		
		se.submit()
		
		# check if available qty is increased
		actual_qty_2 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)
		
		return se
	
	def test_sales_invoice_return_of_non_packing_item(self):
		self._test_sales_invoice_return("_Test Item", 5, 2)
			
	def test_sales_invoice_return_of_packing_item(self):
		self._test_sales_invoice_return("_Test Sales BOM Item", 25, 20)
		
	def _test_delivery_note_return(self, item_code, delivered_qty, returned_qty):
		self._insert_material_receipt()
		
		from stock.doctype.delivery_note.test_delivery_note \
			import test_records as delivery_note_test_records
		
		actual_qty_0 = self._get_actual_qty()
		
		# make a delivery note based on this invoice
		dn = webnotes.bean(copy=delivery_note_test_records[0])
		dn.doclist[1].item_code = item_code
		dn.insert()
		dn.submit()
		
		actual_qty_1 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)
		
		si_doclist = webnotes.map_doclist([
			["Delivery Note", "Sales Invoice"],
			["Delivery Note Item", "Sales Invoice Item"],
			["Sales Taxes and Charges", "Sales Taxes and Charges"],
			["Sales Team", "Sales Team"]], dn.doc.name)
			
		si = webnotes.bean(si_doclist)
		si.doc.posting_date = dn.doc.posting_date
		si.doc.debit_to = "_Test Customer - _TC"
		for d in si.doclist.get({"parentfield": "entries"}):
			d.income_account = "Sales - _TC"
			d.cost_center = "_Test Cost Center - _TC"
		si.insert()
		si.submit()
		
		# insert and submit stock entry for sales return
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Sales Return"
		se.doc.delivery_note_no = dn.doc.name
		se.doc.posting_date = "2013-03-10"
		se.doc.fiscal_year = "_Test Fiscal Year 2013"
		se.doclist[1].qty = se.doclist[1].transfer_qty = returned_qty
		
		se.insert()
		se.submit()
		
		actual_qty_2 = self._get_actual_qty()
		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)
		
		return se
		
	def test_delivery_note_return_of_non_packing_item(self):
		self._test_delivery_note_return("_Test Item", 5, 2)
		
	def test_delivery_note_return_of_packing_item(self):
		self._test_delivery_note_return("_Test Sales BOM Item", 25, 20)
		
	def _test_sales_return_jv(self, se):
		from stock.doctype.stock_entry.stock_entry import make_return_jv
		jv_list = make_return_jv(se.doc.name)
		
		self.assertEqual(len(jv_list), 3)
		self.assertEqual(jv_list[0].get("voucher_type"), "Credit Note")
		self.assertEqual(jv_list[0].get("posting_date"), se.doc.posting_date)
		self.assertEqual(jv_list[1].get("account"), "_Test Customer - _TC")
		self.assertEqual(jv_list[2].get("account"), "Sales - _TC")
		self.assertTrue(jv_list[1].get("against_invoice"))
		
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
		self._insert_material_receipt()

		from selling.doctype.sales_order.test_sales_order \
			import test_records as sales_order_test_records

		actual_qty_0 = self._get_actual_qty()
		
		so = webnotes.bean(copy=sales_order_test_records[0])
		so.doclist[1].item_code = item_code
		so.doclist[1].qty = 5.0
		so.insert()
		so.submit()
		
		dn_doclist = webnotes.map_doclist([
			["Sales Order", "Delivery Note"],
			["Sales Order Item", "Delivery Note Item"],
			["Sales Taxes and Charges", "Sales Taxes and Charges"],
			["Sales Team", "Sales Team"]], so.doc.name)

		dn = webnotes.bean(dn_doclist)
		dn.doc.status = "Draft"
		dn.doc.posting_date = so.doc.delivery_date
		dn.insert()
		dn.submit()
		
		actual_qty_1 = self._get_actual_qty()

		self.assertEquals(actual_qty_0 - delivered_qty, actual_qty_1)

		si_doclist = webnotes.map_doclist([
			["Sales Order", "Sales Invoice"],
			["Sales Order Item", "Sales Invoice Item"],
			["Sales Taxes and Charges", "Sales Taxes and Charges"],
			["Sales Team", "Sales Team"]], so.doc.name)

		si = webnotes.bean(si_doclist)
		si.doc.posting_date = dn.doc.posting_date
		si.doc.debit_to = "_Test Customer - _TC"
		for d in si.doclist.get({"parentfield": "entries"}):
			d.income_account = "Sales - _TC"
			d.cost_center = "_Test Cost Center - _TC"
		si.insert()
		si.submit()

		# insert and submit stock entry for sales return
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Sales Return"
		se.doc.delivery_note_no = dn.doc.name
		se.doc.posting_date = "2013-03-10"
		se.doc.fiscal_year = "_Test Fiscal Year 2013"
		se.doclist[1].qty = se.doclist[1].transfer_qty = returned_qty

		se.insert()
		se.submit()

		actual_qty_2 = self._get_actual_qty()
		self.assertEquals(actual_qty_1 + returned_qty, actual_qty_2)

		return se
		
	def test_purchase_receipt_return(self):
		self._clear_stock()
		
		actual_qty_0 = self._get_actual_qty()
		
		from stock.doctype.purchase_receipt.test_purchase_receipt \
			import test_records as purchase_receipt_test_records
		
		# submit purchase receipt
		pr = webnotes.bean(copy=purchase_receipt_test_records[0])
		pr.insert()
		pr.submit()
		
		actual_qty_1 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_0 + 10, actual_qty_1)
		
		pi_doclist = webnotes.map_doclist([
			["Purchase Receipt", "Purchase Invoice"],
			["Purchase Receipt Item", "Purchase Invoice Item"],
			["Purchase Taxes and Charges", "Purchase Taxes and Charges"]], pr.doc.name)
			
		pi = webnotes.bean(pi_doclist)
		pi.doc.posting_date = pr.doc.posting_date
		pi.doc.credit_to = "_Test Supplier - _TC"
		for d in pi.doclist.get({"parentfield": "entries"}):
			d.expense_head = "_Test Account Cost for Goods Sold - _TC"
			d.cost_center = "_Test Cost Center - _TC"
		for d in pi.doclist.get({"parentfield": "purchase_tax_details"}):
			d.cost_center = "_Test Cost Center - _TC"
		
		pi.run_method("calculate_taxes_and_totals")
		pi.insert()
		pi.submit()
		
		# submit purchase return
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Purchase Return"
		se.doc.purchase_receipt_no = pr.doc.name
		se.doc.posting_date = "2013-03-01"
		se.doc.fiscal_year = "_Test Fiscal Year 2013"
		se.doclist[1].qty = se.doclist[1].transfer_qty = 5
		se.doclist[1].s_warehouse = "_Test Warehouse"
		se.insert()
		se.submit()
		
		actual_qty_2 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_1 - 5, actual_qty_2)
		
		webnotes.conn.set_default("company", self.old_default_company)
		
		return se, pr.doc.name
		
	def test_over_stock_return(self):
		from stock.doctype.stock_entry.stock_entry import StockOverReturnError
		
		# out of 10, 5 gets returned
		prev_se, pr_docname = self.test_purchase_receipt_return()
		
		# submit purchase return - return another 6 qtys so that exception is raised
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Purchase Return"
		se.doc.purchase_receipt_no = pr_docname
		se.doc.posting_date = "2013-03-01"
		se.doc.fiscal_year = "_Test Fiscal Year 2013"
		se.doclist[1].qty = se.doclist[1].transfer_qty = 6
		se.doclist[1].s_warehouse = "_Test Warehouse"
		
		self.assertRaises(StockOverReturnError, se.insert)
		
	def _test_purchase_return_jv(self, se):
		from stock.doctype.stock_entry.stock_entry import make_return_jv
		jv_list = make_return_jv(se.doc.name)
		
		self.assertEqual(len(jv_list), 3)
		self.assertEqual(jv_list[0].get("voucher_type"), "Debit Note")
		self.assertEqual(jv_list[0].get("posting_date"), se.doc.posting_date)
		self.assertEqual(jv_list[1].get("account"), "_Test Supplier - _TC")
		self.assertEqual(jv_list[2].get("account"), "_Test Account Cost for Goods Sold - _TC")
		self.assertTrue(jv_list[1].get("against_voucher"))
		
	def test_make_return_jv_for_purchase_receipt(self):
		se, pr_name = self.test_purchase_receipt_return()
		self._test_purchase_return_jv(se)

		se, pr_name = self._test_purchase_return_return_against_purchase_order()
		self._test_purchase_return_jv(se)
		
	def _test_purchase_return_return_against_purchase_order(self):
		self._clear_stock()
		
		actual_qty_0 = self._get_actual_qty()
		
		from buying.doctype.purchase_order.test_purchase_order \
			import test_records as purchase_order_test_records
		
		# submit purchase receipt
		po = webnotes.bean(copy=purchase_order_test_records[0])
		po.doc.is_subcontracted = None
		po.doclist[1].item_code = "_Test Item"
		po.doclist[1].import_rate = 50
		po.insert()
		po.submit()
		
		pr_doclist = webnotes.map_doclist([
			["Purchase Order", "Purchase Receipt"],
			["Purchase Order Item", "Purchase Receipt Item"],
			["Purchase Taxes and Charges", "Purchase Taxes and Charges"]], po.doc.name)
		
		pr = webnotes.bean(pr_doclist)
		pr.doc.posting_date = po.doc.transaction_date
		pr.insert()
		pr.submit()
		
		actual_qty_1 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_0 + 10, actual_qty_1)
		
		pi_doclist = webnotes.map_doclist([
			["Purchase Order", "Purchase Invoice"],
			["Purchase Order Item", "Purchase Invoice Item"],
			["Purchase Taxes and Charges", "Purchase Taxes and Charges"]], po.doc.name)
			
		pi = webnotes.bean(pi_doclist)
		pi.doc.posting_date = pr.doc.posting_date
		pi.doc.credit_to = "_Test Supplier - _TC"
		for d in pi.doclist.get({"parentfield": "entries"}):
			d.expense_head = "_Test Account Cost for Goods Sold - _TC"
			d.cost_center = "_Test Cost Center - _TC"
		for d in pi.doclist.get({"parentfield": "purchase_tax_details"}):
			d.cost_center = "_Test Cost Center - _TC"
		
		pi.run_method("calculate_taxes_and_totals")
		pi.insert()
		pi.submit()
		
		# submit purchase return
		se = webnotes.bean(copy=test_records[0])
		se.doc.purpose = "Purchase Return"
		se.doc.purchase_receipt_no = pr.doc.name
		se.doc.posting_date = "2013-03-01"
		se.doc.fiscal_year = "_Test Fiscal Year 2013"
		se.doclist[1].qty = se.doclist[1].transfer_qty = 5
		se.doclist[1].s_warehouse = "_Test Warehouse"
		se.insert()
		se.submit()
		
		actual_qty_2 = self._get_actual_qty()
		
		self.assertEquals(actual_qty_1 - 5, actual_qty_2)
		
		webnotes.conn.set_default("company", self.old_default_company)
		
		return se, pr.doc.name
		
test_records = [
	[
		{
			"company": "_Test Company", 
			"doctype": "Stock Entry", 
			"posting_date": "2013-01-25", 
			"posting_time": "17:14:24", 
			"purpose": "Material Receipt",
			"fiscal_year": "_Test Fiscal Year 2013", 
			"expense_adjustment_account": "Stock Adjustment - _TC"
		}, 
		{
			"conversion_factor": 1.0, 
			"doctype": "Stock Entry Detail", 
			"item_code": "_Test Item", 
			"parentfield": "mtn_details", 
			"incoming_rate": 100,
			"qty": 50.0, 
			"stock_uom": "_Test UOM", 
			"transfer_qty": 50.0, 
			"uom": "_Test UOM",
			"t_warehouse": "_Test Warehouse",
		}, 
	],
	[
		{
			"company": "_Test Company", 
			"doctype": "Stock Entry", 
			"posting_date": "2013-01-25", 
			"posting_time": "17:15", 
			"purpose": "Material Issue",
			"fiscal_year": "_Test Fiscal Year 2013", 
			"expense_adjustment_account": "Stock Adjustment - _TC"
		}, 
		{
			"conversion_factor": 1.0, 
			"doctype": "Stock Entry Detail", 
			"item_code": "_Test Item", 
			"parentfield": "mtn_details", 
			"incoming_rate": 100,
			"qty": 40.0, 
			"stock_uom": "_Test UOM", 
			"transfer_qty": 40.0, 
			"uom": "_Test UOM",
			"s_warehouse": "_Test Warehouse",
		}, 
	],
	[
		{
			"company": "_Test Company", 
			"doctype": "Stock Entry", 
			"posting_date": "2013-01-25", 
			"posting_time": "17:14:24", 
			"purpose": "Material Transfer",
			"fiscal_year": "_Test Fiscal Year 2013", 
			"expense_adjustment_account": "Stock Adjustment - _TC"
		}, 
		{
			"conversion_factor": 1.0, 
			"doctype": "Stock Entry Detail", 
			"item_code": "_Test Item", 
			"parentfield": "mtn_details", 
			"incoming_rate": 100,
			"qty": 45.0, 
			"stock_uom": "_Test UOM", 
			"transfer_qty": 45.0, 
			"uom": "_Test UOM",
			"s_warehouse": "_Test Warehouse",
			"t_warehouse": "_Test Warehouse 1",
		}
	]
]