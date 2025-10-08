import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate

from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.gross_profit.gross_profit import execute
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.accounts.report.gross_profit import gross_profit as rpt


class TestGrossProfit(FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_item()
		self.create_bundle()
		self.create_customer()
		self.create_sales_invoice()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def create_company(self):
		company_name = "_Test Company"
		abbr = "_TC"
		if frappe.db.exists("Company", company_name):
			company = frappe.get_doc("Company", company_name)
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": company_name,
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			)
			company = company.save()

		self.company = company.name
		self.cost_center = company.cost_center
		self.warehouse = "Stores - " + abbr
		self.finished_warehouse = "Finished Goods - " + abbr
		self.income_account = "Sales - " + abbr
		self.expense_account = "Cost of Goods Sold - " + abbr
		self.debit_to = "Debtors - " + abbr
		self.creditors = "Creditors - " + abbr

	def create_item(self):
		item = create_item(
			item_code="_Test GP Item", is_stock_item=1, company=self.company, warehouse=self.warehouse
		)
		self.item = item if isinstance(item, str) else item.item_code

	def create_bundle(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle

		item2 = create_item(
			item_code="_Test GP Item 2", is_stock_item=1, company=self.company, warehouse=self.warehouse
		)
		self.item2 = item2 if isinstance(item2, str) else item2.item_code

		# This will be parent item
		bundle = create_item(
			item_code="_Test GP bundle", is_stock_item=0, company=self.company, warehouse=self.warehouse
		)
		self.bundle = bundle if isinstance(bundle, str) else bundle.item_code

		# Create Product Bundle
		self.product_bundle = make_product_bundle(parent=self.bundle, items=[self.item, self.item2])

	def create_customer(self):
		name = "_Test GP Customer"
		if frappe.db.exists("Customer", name):
			self.customer = name
		else:
			customer = frappe.new_doc("Customer")
			customer.customer_name = name
			customer.type = "Individual"
			customer.save()
			self.customer = customer.name

	def create_sales_invoice(
		self, qty=1, rate=100, posting_date=None, do_not_save=False, do_not_submit=False
	):
		"""
		Helper function to populate default values in sales invoice
		"""
		if posting_date is None:
			posting_date = nowdate()

		sinv = create_sales_invoice(
			qty=qty,
			rate=rate,
			company=self.company,
			customer=self.customer,
			item_code=self.item,
			item_name=self.item,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			update_stock=0,
			currency="INR",
			is_pos=0,
			is_return=0,
			return_against=None,
			income_account=self.income_account,
			expense_account=self.expense_account,
			do_not_save=do_not_save,
			do_not_submit=do_not_submit,
		)
		return sinv

	def create_delivery_note(
		self, item=None, qty=1, rate=100, posting_date=None, do_not_save=False, do_not_submit=False
	):
		"""
		Helper function to populate default values in Delivery Note
		"""
		if posting_date is None:
			posting_date = nowdate()

		dnote = create_delivery_note(
			company=self.company,
			customer=self.customer,
			currency="INR",
			item=item or self.item,
			qty=qty,
			rate=rate,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			return_against=None,
			expense_account=self.expense_account,
			do_not_save=do_not_save,
			do_not_submit=do_not_submit,
		)
		return dnote

	def clear_old_entries(self):
		doctype_list = [
			"Sales Invoice",
			"GL Entry",
			"Payment Ledger Entry",
			"Stock Entry",
			"Stock Ledger Entry",
			"Delivery Note",
		]
		for doctype in doctype_list:
			qb.from_(qb.DocType(doctype)).delete().where(qb.DocType(doctype).company == self.company).run()

	def test_invoice_without_only_delivery_note(self):
		"""
		Test buying amount for Invoice without `update_stock` flag set but has Delivery Note
		"""
		se = make_stock_entry(
			company=self.company,
			item_code=self.item,
			target=self.warehouse,
			qty=1,
			basic_rate=100,
			do_not_submit=True,
		)
		item = se.items[0]
		se.append(
			"items",
			{
				"item_code": item.item_code,
				"s_warehouse": item.s_warehouse,
				"t_warehouse": item.t_warehouse,
				"qty": 1,
				"basic_rate": 200,
				"conversion_factor": item.conversion_factor or 1.0,
				"transfer_qty": flt(item.qty) * (flt(item.conversion_factor) or 1.0),
				"serial_no": item.serial_no,
				"batch_no": item.batch_no,
				"cost_center": item.cost_center,
				"expense_account": item.expense_account,
			},
		)
		se = se.save().submit()

		sinv = create_sales_invoice(
			qty=1,
			rate=100,
			company=self.company,
			customer=self.customer,
			item_code=self.item,
			item_name=self.item,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			update_stock=0,
			currency="INR",
			income_account=self.income_account,
			expense_account=self.expense_account,
		)

		filters = frappe._dict(
			company=self.company, from_date=nowdate(), to_date=nowdate(), group_by="Invoice"
		)

		columns, data = execute(filters=filters)

		# Without Delivery Note, buying rate should be 150
		expected_entry_without_dn = {
			"parent_invoice": sinv.name,
			"currency": "INR",
			"sales_invoice": self.item,
			"customer": self.customer,
			"posting_date": frappe.utils.datetime.date.fromisoformat(nowdate()),
			"item_code": self.item,
			"item_name": self.item,
			"warehouse": "Stores - _GP",
			"qty": 1.0,
			"avg._selling_rate": 100.0,
			"valuation_rate": 150.0,
			"selling_amount": 100.0,
			"buying_amount": 150.0,
			"gross_profit": -50.0,
			"gross_profit_%": -50.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		self.assertDictContainsSubset(expected_entry_without_dn, gp_entry[0])

		# make delivery note
		dn = make_delivery_note(sinv.name)
		dn.items[0].qty = 1
		dn = dn.save().submit()

		columns, data = execute(filters=filters)

		# Without Delivery Note, buying rate should be 100
		expected_entry_with_dn = {
			"parent_invoice": sinv.name,
			"currency": "INR",
			"sales_invoice": self.item,
			"customer": self.customer,
			"posting_date": frappe.utils.datetime.date.fromisoformat(nowdate()),
			"item_code": self.item,
			"item_name": self.item,
			"warehouse": "Stores - _GP",
			"qty": 1.0,
			"avg._selling_rate": 100.0,
			"valuation_rate": 100.0,
			"selling_amount": 100.0,
			"buying_amount": 100.0,
			"gross_profit": 0.0,
			"gross_profit_%": 0.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		self.assertDictContainsSubset(expected_entry_with_dn, gp_entry[0])

	def test_bundled_delivery_note_with_different_warehouses(self):
		"""
		Test Delivery Note with bundled item. Packed Item from the bundle having different warehouses
		"""
		se = make_stock_entry(
			company=self.company,
			item_code=self.item,
			target=self.warehouse,
			qty=1,
			basic_rate=100,
			do_not_submit=True,
		)
		item = se.items[0]
		se.append(
			"items",
			{
				"item_code": self.item2,
				"s_warehouse": "",
				"t_warehouse": self.finished_warehouse,
				"qty": 1,
				"basic_rate": 100,
				"conversion_factor": item.conversion_factor or 1.0,
				"transfer_qty": flt(item.qty) * (flt(item.conversion_factor) or 1.0),
				"serial_no": item.serial_no,
				"batch_no": item.batch_no,
				"cost_center": item.cost_center,
				"expense_account": item.expense_account,
			},
		)
		se = se.save().submit()

		# Make a Delivery note with Product bundle
		# Packed Items will have different warehouses
		dnote = self.create_delivery_note(item=self.bundle, qty=1, rate=200, do_not_submit=True)
		dnote.packed_items[1].warehouse = self.finished_warehouse
		dnote = dnote.submit()

		# make Sales Invoice for above delivery note
		sinv = make_sales_invoice(dnote.name)
		sinv = sinv.save().submit()

		filters = frappe._dict(
			company=self.company,
			from_date=nowdate(),
			to_date=nowdate(),
			group_by="Invoice",
			sales_invoice=sinv.name,
		)

		columns, data = execute(filters=filters)
		self.assertGreater(len(data), 0)

	def test_order_connected_dn_and_inv(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		"""
			Test gp calculation when invoice and delivery note aren't directly connected.
			SO -- INV
			|
			DN
		"""
		se = make_stock_entry(
			company=self.company,
			item_code=self.item,
			target=self.warehouse,
			qty=3,
			basic_rate=100,
			do_not_submit=True,
		)
		item = se.items[0]
		se.append(
			"items",
			{
				"item_code": item.item_code,
				"s_warehouse": item.s_warehouse,
				"t_warehouse": item.t_warehouse,
				"qty": 10,
				"basic_rate": 200,
				"conversion_factor": item.conversion_factor or 1.0,
				"transfer_qty": flt(item.qty) * (flt(item.conversion_factor) or 1.0),
				"serial_no": item.serial_no,
				"batch_no": item.batch_no,
				"cost_center": item.cost_center,
				"expense_account": item.expense_account,
			},
		)
		se = se.save().submit()

		so = make_sales_order(
			customer=self.customer,
			company=self.company,
			warehouse=self.warehouse,
			item=self.item,
			qty=4,
			do_not_save=False,
			do_not_submit=False,
		)

		from erpnext.selling.doctype.sales_order.sales_order import (
			make_delivery_note,
			make_sales_invoice,
		)

		make_delivery_note(so.name).submit()
		sinv = make_sales_invoice(so.name).submit()

		filters = frappe._dict(
			company=self.company, from_date=nowdate(), to_date=nowdate(), group_by="Invoice"
		)

		columns, data = execute(filters=filters)
		expected_entry = {
			"parent_invoice": sinv.name,
			"currency": "INR",
			"sales_invoice": self.item,
			"customer": self.customer,
			"posting_date": frappe.utils.datetime.date.fromisoformat(nowdate()),
			"item_code": self.item,
			"item_name": self.item,
			"warehouse": "Stores - _GP",
			"qty": 4.0,
			"avg._selling_rate": 100.0,
			"valuation_rate": 125.0,
			"selling_amount": 400.0,
			"buying_amount": 500.0,
			"gross_profit": -100.0,
			"gross_profit_%": -25.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		self.assertDictContainsSubset(expected_entry, gp_entry[0])

	def test_crnote_against_invoice_with_multiple_instances_of_same_item(self):
		"""
		Item Qty for Sales Invoices with multiple instances of same item go in the -ve. Ideally, the credit noteshould cancel out the invoice items.
		"""
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

		# Invoice with an item added twice
		sinv = self.create_sales_invoice(qty=1, rate=100, posting_date=nowdate(), do_not_submit=True)
		sinv.append("items", frappe.copy_doc(sinv.items[0], ignore_no_copy=False))
		sinv = sinv.save().submit()

		# Create Credit Note for Invoice
		cr_note = make_sales_return(sinv.name)
		cr_note = cr_note.save().submit()

		filters = frappe._dict(
			company=self.company, from_date=nowdate(), to_date=nowdate(), group_by="Invoice"
		)

		columns, data = execute(filters=filters)
		expected_entry = {
			"parent_invoice": sinv.name,
			"currency": "INR",
			"sales_invoice": self.item,
			"customer": self.customer,
			"posting_date": frappe.utils.datetime.date.fromisoformat(nowdate()),
			"item_code": self.item,
			"item_name": self.item,
			"warehouse": "Stores - _GP",
			"qty": 0.0,
			"avg._selling_rate": 100,
			"valuation_rate": 0.0,
			"selling_amount": 0.0,
			"buying_amount": 0.0,
			"gross_profit": 0.0,
			"gross_profit_%": 0.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		# Both items of Invoice should have '0' qty
		self.assertEqual(len(gp_entry), 2)
		self.assertDictContainsSubset(expected_entry, gp_entry[0])
		self.assertDictContainsSubset(expected_entry, gp_entry[1])

	def test_standalone_cr_notes(self):
		"""
		Standalone cr notes will be reported as usual
		"""
		# Make Cr Note
		sinv = self.create_sales_invoice(
			qty=-1, rate=100, posting_date=nowdate(), do_not_save=True, do_not_submit=True
		)
		sinv.is_return = 1
		sinv = sinv.save().submit()

		filters = frappe._dict(
			company=self.company, from_date=nowdate(), to_date=nowdate(), group_by="Invoice"
		)

		columns, data = execute(filters=filters)
		expected_entry = {
			"parent_invoice": sinv.name,
			"currency": "INR",
			"sales_invoice": self.item,
			"customer": self.customer,
			"posting_date": frappe.utils.datetime.date.fromisoformat(nowdate()),
			"item_code": self.item,
			"item_name": self.item,
			"warehouse": "Stores - _GP",
			"qty": -1.0,
			"avg._selling_rate": 100.0,
			"valuation_rate": 0.0,
			"selling_amount": -100.0,
			"buying_amount": 0.0,
			"gross_profit": -100.0,
			"gross_profit_%": 100.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		self.assertDictContainsSubset(expected_entry, gp_entry[0])

	def test_different_rates_in_si_and_dn(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		"""
			Test gp calculation when invoice and delivery note differ in qty and aren't connected
			SO -- INV
			|
			DN
		"""
		se = make_stock_entry(
			company=self.company,
			item_code=self.item,
			target=self.warehouse,
			qty=3,
			basic_rate=700,
			do_not_submit=True,
		)
		item = se.items[0]
		se.append(
			"items",
			{
				"item_code": item.item_code,
				"s_warehouse": item.s_warehouse,
				"t_warehouse": item.t_warehouse,
				"qty": 10,
				"basic_rate": 700,
				"conversion_factor": item.conversion_factor or 1.0,
				"transfer_qty": flt(item.qty) * (flt(item.conversion_factor) or 1.0),
				"serial_no": item.serial_no,
				"batch_no": item.batch_no,
				"cost_center": item.cost_center,
				"expense_account": item.expense_account,
			},
		)
		se = se.save().submit()

		so = make_sales_order(
			customer=self.customer,
			company=self.company,
			warehouse=self.warehouse,
			item=self.item,
			rate=800,
			qty=10,
			do_not_save=False,
			do_not_submit=False,
		)

		from erpnext.selling.doctype.sales_order.sales_order import (
			make_delivery_note,
			make_sales_invoice,
		)

		dn1 = make_delivery_note(so.name)
		dn1.items[0].qty = 4
		dn1.items[0].rate = 800
		dn1.save().submit()

		dn2 = make_delivery_note(so.name)
		dn2.items[0].qty = 6
		dn2.items[0].rate = 800
		dn2.save().submit()

		sinv = make_sales_invoice(so.name)
		sinv.items[0].qty = 4
		sinv.items[0].rate = 800
		sinv.save().submit()

		filters = frappe._dict(
			company=self.company, from_date=nowdate(), to_date=nowdate(), group_by="Invoice"
		)

		columns, data = execute(filters=filters)
		expected_entry = {
			"parent_invoice": sinv.name,
			"currency": "INR",
			"sales_invoice": self.item,
			"customer": self.customer,
			"posting_date": frappe.utils.datetime.date.fromisoformat(nowdate()),
			"item_code": self.item,
			"item_name": self.item,
			"warehouse": "Stores - _GP",
			"qty": 4.0,
			"avg._selling_rate": 800.0,
			"valuation_rate": 700.0,
			"selling_amount": 3200.0,
			"buying_amount": 2800.0,
			"gross_profit": 400.0,
			"gross_profit_%": 12.5,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		self.assertDictContainsSubset(expected_entry, gp_entry[0])

	def test_valuation_rate_without_previous_sle(self):
		"""
		Test Valuation rate calculation when stock ledger is empty and invoices are against different warehouses
		"""
		stock_settings = frappe.get_doc("Stock Settings")
		stock_settings.valuation_method = "FIFO"
		stock_settings.save()

		item = create_item(
			item_code="_Test Wirebound Notebook",
			is_stock_item=1,
		)
		item.allow_negative_stock = True
		item.save()
		self.item = item.item_code

		item.reload()
		item.valuation_rate = 1900
		item.save()
		sinv1 = self.create_sales_invoice(qty=1, rate=2000, posting_date=nowdate(), do_not_submit=True)
		sinv1.update_stock = 1
		sinv1.set_warehouse = self.warehouse
		sinv1.items[0].warehouse = self.warehouse
		sinv1.save().submit()

		item.reload()
		item.valuation_rate = 1800
		item.save()
		sinv2 = self.create_sales_invoice(qty=1, rate=2000, posting_date=nowdate(), do_not_submit=True)
		sinv2.update_stock = 1
		sinv2.set_warehouse = self.finished_warehouse
		sinv2.items[0].warehouse = self.finished_warehouse
		sinv2.save().submit()

		filters = frappe._dict(
			company=self.company, from_date=nowdate(), to_date=nowdate(), group_by="Invoice"
		)
		columns, data = execute(filters=filters)

		item_from_sinv1 = [x for x in data if x.parent_invoice == sinv1.name]
		self.assertEqual(len(item_from_sinv1), 1)
		self.assertEqual(1900, item_from_sinv1[0].valuation_rate)

		item_from_sinv2 = [x for x in data if x.parent_invoice == sinv2.name]
		self.assertEqual(len(item_from_sinv2), 1)
		self.assertEqual(1800, item_from_sinv2[0].valuation_rate)

	def test_gross_profit_groupby_invoices(self):
		create_sales_invoice(
			qty=1,
			rate=100,
			company=self.company,
			customer=self.customer,
			item_code=self.item,
			item_name=self.item,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			update_stock=0,
			currency="INR",
			income_account=self.income_account,
			expense_account=self.expense_account,
		)
		filters = frappe._dict(
			company=self.company, from_date=nowdate(), to_date=nowdate(), group_by="Invoice"
		)
		_, data = execute(filters=filters)
		total = data[-1]
		self.assertEqual(total.selling_amount, 100.0)
		self.assertEqual(total.buying_amount, 0.0)
		self.assertEqual(total.gross_profit, 100.0)
		self.assertEqual(total.get("gross_profit_%"), 100.0)
	
	def test_process_dn_detail_branch_updates_from_dn_packed_item_TC_ACC_402(self):
		cust = self.customer
		wh_stores = self.warehouse
		wh_finished = self.finished_warehouse

		orig_li = rpt.GrossProfitGenerator.load_invoice_items
		orig_gdn = rpt.GrossProfitGenerator.get_delivery_notes
		orig_lpb = rpt.GrossProfitGenerator.load_product_bundle
		orig_lnsi = rpt.GrossProfitGenerator.load_non_stock_items
		orig_gr = rpt.GrossProfitGenerator.get_returned_invoice_items
		orig_gba = rpt.GrossProfitGenerator.get_buying_amount

		# --- patches ---
		def fake_load_invoice_items(gen_self):
			gen_self.si_list = [
				frappe._dict(
					parenttype="Sales Invoice",
					parent=None,                     
					parent_invoice="BUNDLE-1",      
					posting_date=frappe.utils.getdate(),
					posting_time="10:00:00",
					project=None,
					update_stock=0,                  
					customer=cust,
					customer_group="All Customer Groups",
					territory="All Territories",
					item_code="_Test GP Item",
					invoice_base_net_total=0,
					item_name="_Test GP Item",
					description="desc",
					warehouse=wh_stores,             
					item_group="All Item Groups",
					brand="",
					so_detail=None,
					sales_order=None,
					dn_detail="DN-ROW-1",            
					delivery_note="DN-1",
					qty=2,
					base_net_amount=10,             
					name="SII-ROW-1",
					is_return=0,
					cost_center=None,
					serial_and_batch_bundle=None,
					indent=1.0,                      
				)
			]

		def fake_get_delivery_notes(gen_self):
			gen_self.delivery_notes = {}

		def fake_load_product_bundle(gen_self):
			
			gen_self.product_bundles = {
				"Delivery Note": {
					"DN-1": {
						"BUNDLE-1": [
							frappe._dict(
								item_code="_Test GP Item",
								parent_detail_docname="DN-ROW-1",
								warehouse=wh_finished, 
								base_amount=777,       
								total_qty=-2,
								serial_and_batch_bundle=None,
							)
						]
					}
				}
			}

		def fake_load_non_stock_items(gen_self):
			gen_self.non_stock_items = []

		def fake_get_returned_invoice_items(gen_self):
			gen_self.returned_invoices = frappe._dict()

		def fake_get_buying_amount(gen_self, row, item_code):
			
			return 0

		# apply patches
		rpt.GrossProfitGenerator.load_invoice_items = fake_load_invoice_items
		rpt.GrossProfitGenerator.get_delivery_notes = fake_get_delivery_notes
		rpt.GrossProfitGenerator.load_product_bundle = fake_load_product_bundle
		rpt.GrossProfitGenerator.load_non_stock_items = fake_load_non_stock_items
		rpt.GrossProfitGenerator.get_returned_invoice_items = fake_get_returned_invoice_items
		rpt.GrossProfitGenerator.get_buying_amount = fake_get_buying_amount

		try:
			filters = frappe._dict({
				"company": self.company,
				"group_by": "Item Code",
				"to_date": frappe.utils.nowdate(),
			})

			gp = rpt.GrossProfitGenerator(filters)

			row = gp.si_list[0]
			self.assertEqual(row.item_row, "DN-ROW-1")      
			self.assertEqual(row.warehouse, wh_finished)     
			self.assertEqual(row.base_amount, 777)          
		finally:
			# restore
			rpt.GrossProfitGenerator.load_invoice_items = orig_li
			rpt.GrossProfitGenerator.get_delivery_notes = orig_gdn
			rpt.GrossProfitGenerator.load_product_bundle = orig_lpb
			rpt.GrossProfitGenerator.load_non_stock_items = orig_lnsi
			rpt.GrossProfitGenerator.get_returned_invoice_items = orig_gr
			rpt.GrossProfitGenerator.get_buying_amount = orig_gba

	def test_update_return_invoices_both_paths_TC_ACC_403(self):
	
		comp = self.company

		orig_li  = rpt.GrossProfitGenerator.load_invoice_items
		orig_gdn = rpt.GrossProfitGenerator.get_delivery_notes
		orig_lpb = rpt.GrossProfitGenerator.load_product_bundle
		orig_ln  = rpt.GrossProfitGenerator.load_non_stock_items
		orig_gr  = rpt.GrossProfitGenerator.get_returned_invoice_items
		orig_gba = rpt.GrossProfitGenerator.get_buying_amount

		# ---- patches ----
		def fake_load_invoice_items(gen_self):
			gen_self.si_list = [
				frappe._dict(
					parenttype="Sales Invoice",
					parent="INV-1",                
					parent_invoice=None,
					posting_date=frappe.utils.getdate(),
					posting_time="10:00:00",
					project=None,
					update_stock=0,
					customer="_Test GP Customer",
					customer_group="All Customer Groups",
					territory="All Territories",
					item_code="ITEM-A",
					invoice_base_net_total=0,
					item_name="Item A",
					description="A",
					warehouse="Stores - _GP",
					item_group="All Item Groups",
					brand="",
					so_detail=None,
					sales_order=None,
					dn_detail=None,                
					delivery_note=None,
					qty=2,                         
					base_net_amount=300,            
					name="SII-A",
					is_return=0,
					cost_center=None,
					serial_and_batch_bundle=None,
					indent=1.0,
				),
				frappe._dict(
					parenttype="Sales Invoice",
					parent="INV-2",
					parent_invoice=None,
					posting_date=frappe.utils.getdate(),
					posting_time="10:00:00",
					project=None,
					update_stock=0,
					customer="_Test GP Customer",
					customer_group="All Customer Groups",
					territory="All Territories",
					item_code="ITEM-B",
					invoice_base_net_total=0,
					item_name="Item B",
					description="B",
					warehouse="Stores - _GP",
					item_group="All Item Groups",
					brand="",
					so_detail=None,
					sales_order=None,
					dn_detail=None,
					delivery_note=None,
					qty=1,                          
					base_net_amount=100,
					name="SII-B",
					is_return=0,
					cost_center=None,
					serial_and_batch_bundle=None,
					indent=1.0,
				),
			]

		def fake_get_delivery_notes(gen_self):
			gen_self.delivery_notes = {}

		def fake_load_product_bundle(gen_self):
			gen_self.product_bundles = {}

		def fake_load_non_stock_items(gen_self):
			gen_self.non_stock_items = []

		def fake_get_returned_invoice_items(gen_self):
			gen_self.returned_invoices = frappe._dict({
				"INV-1": frappe._dict({
					"ITEM-A": [frappe._dict(qty=-1, base_amount=-150)]
				}),
				"INV-2": frappe._dict({
					"ITEM-B": [frappe._dict(qty=-2, base_amount=-300)]
				}),
			})

		def fake_get_buying_amount(gen_self, row, item_code):
			return 200 if item_code == "ITEM-A" else 300

		# apply patches
		rpt.GrossProfitGenerator.load_invoice_items = fake_load_invoice_items
		rpt.GrossProfitGenerator.get_delivery_notes = fake_get_delivery_notes
		rpt.GrossProfitGenerator.load_product_bundle = fake_load_product_bundle
		rpt.GrossProfitGenerator.load_non_stock_items = fake_load_non_stock_items
		rpt.GrossProfitGenerator.get_returned_invoice_items = fake_get_returned_invoice_items
		rpt.GrossProfitGenerator.get_buying_amount = fake_get_buying_amount

		try:
			filters = frappe._dict({
				"company": comp,
				"group_by": "Item Code",
				"from_date": nowdate(),
				"to_date": nowdate(),
			})
			gp = rpt.GrossProfitGenerator(filters)

			row_a = next(r for r in gp.si_list if r.item_code == "ITEM-A")
			self.assertEqual(row_a.qty, 1)             
			self.assertEqual(row_a.base_amount, 150)    
			self.assertEqual(row_a.buying_rate, 100)     
			self.assertEqual(row_a.buying_amount, 100)   

			ret_a = gp.returned_invoices["INV-1"]["ITEM-A"][0]
			self.assertEqual(ret_a.qty, 0)
			self.assertEqual(ret_a.base_amount, 0)

			# B)
			row_b = next(r for r in gp.si_list if r.item_code == "ITEM-B")
			self.assertEqual(row_b.qty, 0)         
			self.assertEqual(row_b.base_amount, 0)      
			self.assertEqual(row_b.buying_amount, 0)    

			ret_b = gp.returned_invoices["INV-2"]["ITEM-B"][0]
			self.assertEqual(ret_b.qty, -2)
			self.assertEqual(ret_b.base_amount, -300)

		finally:
			# restore originals
			rpt.GrossProfitGenerator.load_invoice_items = orig_li
			rpt.GrossProfitGenerator.get_delivery_notes = orig_gdn
			rpt.GrossProfitGenerator.load_product_bundle = orig_lpb
			rpt.GrossProfitGenerator.load_non_stock_items = orig_ln
			rpt.GrossProfitGenerator.get_returned_invoice_items = orig_gr
			rpt.GrossProfitGenerator.get_buying_amount = orig_gba

	def test_payment_term_grouping_portion_paths_and_averages_TC_ACC_404(self):
		# Make rounding deterministic
		orig_get_default = frappe.db.get_default
		def fake_get_default(key, *args, **kwargs):
			if key in ("currency_precision", "float_precision"):
				return 2
			return orig_get_default(key, *args, **kwargs)

		# Keep originals to restore
		orig_li  = rpt.GrossProfitGenerator.load_invoice_items
		orig_gdn = rpt.GrossProfitGenerator.get_delivery_notes
		orig_lpb = rpt.GrossProfitGenerator.load_product_bundle
		orig_ln  = rpt.GrossProfitGenerator.load_non_stock_items
		orig_gr  = rpt.GrossProfitGenerator.get_returned_invoice_items
		orig_gba = rpt.GrossProfitGenerator.get_buying_amount

		# --- patches ---
		def fake_load_invoice_items(gen_self):
			gen_self.si_list = [
				frappe._dict(
					parenttype="Sales Invoice",
					parent="INV-A",
					posting_date=frappe.utils.getdate(),
					posting_time="10:00:00",
					project=None,
					update_stock=0,
					customer="_Test GP Customer",
					customer_group="All Customer Groups",
					territory="All Territories",
					payment_term="NET30",
					item_code="IT-A",
					invoice_base_net_total=0,
					item_name="IT-A",
					description="",
					warehouse=self.warehouse,
					item_group="All Item Groups",
					brand="",
					so_detail=None,
					sales_order=None,
					dn_detail=None,
					delivery_note=None,
					qty=2,
					base_net_amount=200,    
					name="ROW-A",
					is_return=1,           
					invoice_portion=None,
					payment_amount=None,
					cost_center=None,
					serial_and_batch_bundle=None,
					indent=1.0,
				),
				frappe._dict(
					parenttype="Sales Invoice",
					parent="INV-B",
					posting_date=frappe.utils.getdate(),
					posting_time="10:00:00",
					project=None,
					update_stock=0,
					customer="_Test GP Customer",
					customer_group="All Customer Groups",
					territory="All Territories",
					payment_term="NET30",
					item_code="IT-B",
					invoice_base_net_total=0,
					item_name="IT-B",
					description="",
					warehouse=self.warehouse,
					item_group="All Item Groups",
					brand="",
					so_detail=None,
					sales_order=None,
					dn_detail=None,
					delivery_note=None,
					qty=3,
					base_net_amount=300,
					name="ROW-B",
					is_return=0,
					invoice_portion=30,     
					payment_amount=None,
					cost_center=None,
					serial_and_batch_bundle=None,
					indent=1.0,
				),
				frappe._dict(
					parenttype="Sales Invoice",
					parent="INV-C",
					posting_date=frappe.utils.getdate(),
					posting_time="10:00:00",
					project=None,
					update_stock=0,
					customer="_Test GP Customer",
					customer_group="All Customer Groups",
					territory="All Territories",
					payment_term="NET30",
					item_code="IT-C",
					invoice_base_net_total=0,
					item_name="IT-C",
					description="",
					warehouse=self.warehouse,
					item_group="All Item Groups",
					brand="",
					so_detail=None,
					sales_order=None,
					dn_detail=None,
					delivery_note=None,
					qty=4,
					base_net_amount=400,
					name="ROW-C",
					is_return=0,
					invoice_portion=None,
					payment_amount=100,    
					cost_center=None,
					serial_and_batch_bundle=None,
					indent=1.0,
				),
			]

		def fake_get_delivery_notes(gen_self):
			gen_self.delivery_notes = {}

		def fake_load_product_bundle(gen_self):
			gen_self.product_bundles = {}

		def fake_load_non_stock_items(gen_self):
			gen_self.non_stock_items = []

		def fake_get_returned_invoice_items(gen_self):
			gen_self.returned_invoices = frappe._dict()

		def fake_get_buying_amount(gen_self, row, item_code):
			return 120 if item_code == "IT-A" else (150 if item_code == "IT-B" else 200)

		# Apply patches
		frappe.db.get_default = fake_get_default
		rpt.GrossProfitGenerator.load_invoice_items = fake_load_invoice_items
		rpt.GrossProfitGenerator.get_delivery_notes = fake_get_delivery_notes
		rpt.GrossProfitGenerator.load_product_bundle = fake_load_product_bundle
		rpt.GrossProfitGenerator.load_non_stock_items = fake_load_non_stock_items
		rpt.GrossProfitGenerator.get_returned_invoice_items = fake_get_returned_invoice_items
		rpt.GrossProfitGenerator.get_buying_amount = fake_get_buying_amount

		try:
			filters = frappe._dict({
				"company": self.company,
				"group_by": "Payment Term",
				"from_date": frappe.utils.nowdate(),
				"to_date": frappe.utils.nowdate(),
			})

			gp = rpt.GrossProfitGenerator(filters)

			self.assertTrue(gp.grouped_data, "No grouped data produced for Payment Term")
			agg = gp.grouped_data[0]

			self.assertAlmostEqual(agg.base_amount,   390.00, places=2)
			self.assertAlmostEqual(agg.buying_amount, 215.00, places=2)
			self.assertAlmostEqual(agg.gross_profit,  175.00, places=2)
			self.assertAlmostEqual(agg.qty,           9.00,   places=2)

			self.assertAlmostEqual(agg.buying_rate, 23.89, places=2)
			self.assertAlmostEqual(agg.base_rate,   43.33, places=2)
			self.assertAlmostEqual(agg.gross_profit_percent, 44.87, places=2)

		finally:
			# Restore originals
			frappe.db.get_default = orig_get_default
			rpt.GrossProfitGenerator.load_invoice_items = orig_li
			rpt.GrossProfitGenerator.get_delivery_notes = orig_gdn
			rpt.GrossProfitGenerator.load_product_bundle = orig_lpb
			rpt.GrossProfitGenerator.load_non_stock_items = orig_ln
			rpt.GrossProfitGenerator.get_returned_invoice_items = orig_gr
			rpt.GrossProfitGenerator.get_buying_amount = orig_gba

	def test_portion_helper_bundle_buying_and_so_dn_average_in_one_TC_ACC_405(self):
		import frappe
		from frappe.utils import flt

		gp = object.__new__(rpt.GrossProfitGenerator)
		gp.currency_precision = 2

		# -------- 1) set_average_based_on_payment_term_portion ----------
		new_row = frappe._dict(base_amount=0.0, buying_amount=0.0, gross_profit=0.0)

		row_a = frappe._dict(base_amount=100.0, buying_amount=70.0, gross_profit=30.0)
		gp.set_average_based_on_payment_term_portion(new_row, row_a, invoice_portion=20, aggr=False)
		self.assertAlmostEqual(new_row.base_amount,   20.0, places=4)
		self.assertAlmostEqual(new_row.buying_amount, 14.0, places=4)
		self.assertAlmostEqual(new_row.gross_profit,   6.0, places=4)

		row_b = frappe._dict(base_amount=200.0, buying_amount=120.0, gross_profit=80.0)
		gp.set_average_based_on_payment_term_portion(new_row, row_b, invoice_portion=50, aggr=True)
		self.assertAlmostEqual(new_row.base_amount,   120.0, places=4)  # 20 + 100
		self.assertAlmostEqual(new_row.buying_amount,  74.0, places=4)  # 14 + 60
		self.assertAlmostEqual(new_row.gross_profit,   46.0, places=4)  # 6 + 40

		# -------- 2) get_buying_amount_from_product_bundle ----------
		calls = []
		def fake_get_buying_amount(row, item_code):
			calls.append((row.warehouse, row.qty, row.serial_and_batch_bundle, item_code))
			return abs(row.qty) * 10  # easy to check sum

		gp.get_buying_amount = fake_get_buying_amount

		row = frappe._dict(
			item_row="ROW-1", warehouse="W1", qty=99, serial_and_batch_bundle=None,
		)
		product_bundle = [
			frappe._dict(  
				parent_detail_docname="ROW-1",
				warehouse="W2",
				total_qty=3,
				serial_and_batch_bundle="SB-1",
				item_code="IT-MATCH",
			),
			frappe._dict( 
				parent_detail_docname="OTHER",
				warehouse="W3",
				total_qty=5,
				serial_and_batch_bundle=None,
				item_code="IT-NOPE",
			),
		]
		amount = gp.get_buying_amount_from_product_bundle(row, product_bundle)
		self.assertEqual(len(calls), 1)
		w, q, sb, code = calls[0]
		self.assertEqual((w, q, sb, code), ("W2", -3, "SB-1", "IT-MATCH"))
		self.assertAlmostEqual(amount, flt(30.0, gp.currency_precision), places=4)

		# -------- 3) get_buying_amount_from_so_dn ----------
		class _Field:
			def __init__(self, name): self.name = name
			def __eq__(self, other):  
				return ("eq", self.name, other)

		class _DocType:
			def __init__(self, _name):
				self.incoming_rate = _Field("incoming_rate")
				self.docstatus = _Field("docstatus")
				self.item_code = _Field("item_code")
				self.against_sales_order = _Field("against_sales_order")
				self.so_detail = _Field("so_detail")

		class _Query:
			def __init__(self, result):
				self._result = result
			def select(self, *a, **k): return self
			def where(self, *a, **k):  return self
			def groupby(self, *a, **k): return self
			def run(self): return self._result

		class _QB:
			def __init__(self, result): self._result = result
			def DocType(self, name): return _DocType(name)
			def from_(self, doctype): return _Query(self._result)

		orig_qb = frappe.qb
		try:
			# returns an average
			frappe.qb = _QB(result=[(42.5,)])
			val = gp.get_buying_amount_from_so_dn("SO-001", "SO-ROW-1", "IT-1")
			self.assertEqual(val, 42.5)

			frappe.qb = _QB(result=[])
			val2 = gp.get_buying_amount_from_so_dn("SO-001", "SO-ROW-1", "IT-1")
			self.assertEqual(val2, 0)
		finally:
			frappe.qb = orig_qb

	def test_load_invoice_items_all_filter_clauses_TC_ACC_406(self):
		captured_sql = []

		# keep originals
		orig_sql = frappe.db.sql
		orig_gic = rpt.get_item_group_condition
		orig_gccc = rpt.get_cost_centers_with_children
		orig_gad = rpt.get_accounting_dimensions
		orig_gdch = rpt.get_dimension_with_children
		orig_gcv = frappe.get_cached_value
		orig_gv = frappe.db.get_value
		orig_match = rpt.get_match_cond

		# ---- patches ----
		def fake_sql(query, params=None, as_dict=False):
			captured_sql.append(str(query))
			return []

		def fake_get_item_group_condition(item_group):
			return "item.item_group = 'IG-TEST'"

		def fake_get_cc_children(cc_list):
			return ["CC-CHILD-1", "CC-CHILD-2"]

		def fake_get_accounting_dimensions(as_list=False):
			return [
				frappe._dict(fieldname="dim_tree", document_type="DimTree", disabled=0),
				frappe._dict(fieldname="dim_flat", document_type="DimFlat", disabled=0),
			]

		def fake_get_dimension_with_children(dt, vals):
			return ["TREE-A", "TREE-B"]

		def fake_get_cached_value(doctype, name, fieldname):
			if doctype == "DocType" and fieldname == "is_tree":
				return 1 if name == "DimTree" else 0
			return None

		def fake_db_get_value(doctype, name, fields, as_dict=False):
			if doctype == "Warehouse":
				return frappe._dict(lft=1, rgt=9)
			return None

		def fake_match_cond(doctype):
			return "" 

		# apply patches
		frappe.db.sql = fake_sql
		rpt.get_item_group_condition = fake_get_item_group_condition
		rpt.get_cost_centers_with_children = fake_get_cc_children
		rpt.get_accounting_dimensions = fake_get_accounting_dimensions
		rpt.get_dimension_with_children = fake_get_dimension_with_children
		frappe.get_cached_value = fake_get_cached_value
		frappe.db.get_value = fake_db_get_value
		rpt.get_match_cond = fake_match_cond

		try:
			gp = object.__new__(rpt.GrossProfitGenerator)

			# -------- Call 1: Sales Person branch ----------
			gp.filters = frappe._dict(
				company=self.company,
				from_date="2025-08-01",
				to_date="2025-08-31",
				group_by="Sales Person",
				sales_person="SP-1",
				item_group="IG-ROOT",
				item_code="_Test GP Item",
				cost_center='["CC-ROOT"]',
				project='["PR-1"]',
				dim_tree='["X"]',    
				dim_flat='["Y"]',     
				warehouse="WH-ROOT",
			)
			rpt.GrossProfitGenerator.load_invoice_items(gp)
			self.assertTrue(captured_sql, "First SQL not captured")
			q1 = captured_sql[-1]

			self.assertIn("item.item_group = 'IG-TEST'", q1)
			self.assertIn("exists(select 1", q1)
			self.assertIn("st.sales_person = %(sales_person)s", q1)
			self.assertIn("left join `tabSales Team` sales on sales.parent = `tabSales Invoice`.name", q1)
			self.assertIn("sales.sales_person", q1)
			self.assertIn("allocated_amount", q1)
			self.assertIn("and `tabSales Invoice Item`.item_code = %(item_code)s", q1)
			self.assertIn("and `tabSales Invoice Item`.cost_center in %(cost_center)s", q1)
			self.assertIn("and `tabSales Invoice Item`.project in %(project)s", q1)
			self.assertIn("`tabSales Invoice Item`.dim_tree in %(dim_tree)s", q1)
			self.assertIn("`tabSales Invoice Item`.dim_flat in %(dim_flat)s", q1)
			self.assertIn("from `tabWarehouse` wh", q1)
			self.assertIn("wh.lft >= 1", q1)
			self.assertIn("wh.rgt <= 9", q1)

			# -------- Call 2: Payment Term branch ----------
			gp.filters = frappe._dict(
				company=self.company,
				from_date="2025-08-01",
				to_date="2025-08-31",
				group_by="Payment Term",
				item_group="IG-ROOT",
				item_code="_Test GP Item",
				cost_center='["CC-ROOT"]',
				project='["PR-1"]',
				dim_tree='["X"]',
				dim_flat='["Y"]',
				warehouse="WH-ROOT",
			)
			rpt.GrossProfitGenerator.load_invoice_items(gp)
			self.assertGreaterEqual(len(captured_sql), 2, "Second SQL not captured")
			q2 = captured_sql[-1]

			# Assertions for Payment Term variant
			self.assertIn('AS payment_term', q2)  # CASE WHEN ... AS payment_term
			self.assertIn("schedule.invoice_portion", q2)
			self.assertIn("schedule.payment_amount", q2)
			self.assertIn("left join `tabPayment Schedule` schedule", q2)

			# Still includes the other common filters/conditions
			self.assertIn("item.item_group = 'IG-TEST'", q2)
			self.assertIn("and `tabSales Invoice Item`.item_code = %(item_code)s", q2)
			self.assertIn("`tabSales Invoice Item`.dim_tree in %(dim_tree)s", q2)
			self.assertIn("`tabSales Invoice Item`.dim_flat in %(dim_flat)s", q2)
			self.assertIn("from `tabWarehouse` wh", q2)

			self.assertEqual(gp.si_list, [])

		finally:
			# restore patches
			frappe.db.sql = orig_sql
			rpt.get_item_group_condition = orig_gic
			rpt.get_cost_centers_with_children = orig_gccc
			rpt.get_accounting_dimensions = orig_gad
			rpt.get_dimension_with_children = orig_gdch
			frappe.get_cached_value = orig_gcv
			frappe.db.get_value = orig_gv
			rpt.get_match_cond = orig_match