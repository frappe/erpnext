import frappe
from frappe import qb
from frappe.utils import add_days, flt, get_first_day, get_last_day, nowdate

from erpnext.accounts.doctype.sales_invoice.mapper import make_delivery_note, make_sales_return
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.gross_profit.gross_profit import GrossProfitGenerator, execute
from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestGrossProfit(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		self.cost_center = "Main - _TC"
		self.warehouse = "Stores - _TC"
		self.finished_warehouse = "Finished Goods - _TC"
		self.income_account = "Sales - _TC"
		self.expense_account = "Cost of Goods Sold - _TC"
		self.debit_to = "Debtors - _TC"
		self.item = "_Test Item"
		self.item2 = "_Test Item Home Desktop 100"
		self.bundle = "_Test Product Bundle Item"
		self.customer = "_Test Customer"

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
			"warehouse": "Stores - _TC",
			"qty": 1.0,
			"avg._selling_rate": 100.0,
			"valuation_rate": 150.0,
			"selling_amount": 100.0,
			"buying_amount": 150.0,
			"gross_profit": -50.0,
			"gross_profit_%": -50.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		report_output = {k: v for k, v in gp_entry[0].items() if k in expected_entry_without_dn}
		self.assertEqual(report_output, expected_entry_without_dn)

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
			"warehouse": "Stores - _TC",
			"qty": 1.0,
			"avg._selling_rate": 100.0,
			"valuation_rate": 100.0,
			"selling_amount": 100.0,
			"buying_amount": 100.0,
			"gross_profit": 0.0,
			"gross_profit_%": 0.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		report_output = {k: v for k, v in gp_entry[0].items() if k in expected_entry_with_dn}
		self.assertEqual(report_output, expected_entry_with_dn)

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
				"qty": 2,
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

		from erpnext.selling.doctype.sales_order.mapper import (
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
			"warehouse": "Stores - _TC",
			"qty": 4.0,
			"avg._selling_rate": 100.0,
			"valuation_rate": 125.0,
			"selling_amount": 400.0,
			"buying_amount": 500.0,
			"gross_profit": -100.0,
			"gross_profit_%": -25.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		report_output = {k: v for k, v in gp_entry[0].items() if k in expected_entry}
		self.assertEqual(report_output, expected_entry)

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": True})
	def test_crnote_against_invoice_with_multiple_instances_of_same_item(self):
		"""
		Item Qty for Sales Invoices with multiple instances of same item go in the -ve. Ideally, the credit noteshould cancel out the invoice items.
		"""

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
			"warehouse": "Stores - _TC",
			"qty": 0.0,
			"avg._selling_rate": 100.0,
			"valuation_rate": 100.0,
			"selling_amount": 0.0,
			"buying_amount": 0.0,
			"gross_profit": 0.0,
			"gross_profit_%": 0.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		# Both items of Invoice should have '0' qty
		self.assertEqual(len(gp_entry), 2)
		report_output = {k: v for k, v in gp_entry[0].items() if k in expected_entry}
		self.assertEqual(report_output, expected_entry)
		report_output = {k: v for k, v in gp_entry[1].items() if k in expected_entry}
		self.assertEqual(report_output, expected_entry)

	def test_standalone_cr_notes(self):
		"""
		Standalone cr notes will be reported as usual
		"""
		# Make Cr Note
		sinv = self.create_sales_invoice(
			qty=-1, rate=200, posting_date=nowdate(), do_not_save=True, do_not_submit=True
		)
		sinv.is_return = 1
		sinv.items[0].allow_zero_valuation_rate = 1
		sinv = sinv.save().submit()

		filters = frappe._dict(
			company=self.company,
			from_date=nowdate(),
			to_date=nowdate(),
			group_by="Invoice",
			include_returned_invoices=1,
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
			"warehouse": "Stores - _TC",
			"qty": -1.0,
			"avg._selling_rate": 200.0,
			"valuation_rate": 100.0,
			"selling_amount": -200.0,
			"buying_amount": -100.0,
			"gross_profit": -100.0,
			"gross_profit_%": -50.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		report_output = {k: v for k, v in gp_entry[0].items() if k in expected_entry}
		self.assertEqual(report_output, expected_entry)

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

		from erpnext.selling.doctype.sales_order.mapper import (
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
			"warehouse": "Stores - _TC",
			"qty": 4.0,
			"avg._selling_rate": 800.0,
			"valuation_rate": 700.0,
			"selling_amount": 3200.0,
			"buying_amount": 2800.0,
			"gross_profit": 400.0,
			"gross_profit_%": 12.5,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		report_output = {k: v for k, v in gp_entry[0].items() if k in expected_entry}
		self.assertEqual(report_output, expected_entry)

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
			rate=200,
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

		self.assertEqual(total.selling_amount, 200.0)
		self.assertEqual(total.buying_amount, 100.0)
		self.assertEqual(total.gross_profit, 100.0)
		self.assertEqual(total.get("gross_profit_%"), 50.0)

	def test_profit_for_later_period_return(self):
		month_start_date, month_end_date = get_first_day(nowdate()), get_last_day(nowdate())

		sales_inv_date = month_start_date
		return_inv_date = add_days(month_end_date, 1)

		# create sales invoice on month start date
		sinv = self.create_sales_invoice(qty=1, rate=200, do_not_save=True, do_not_submit=True)
		sinv.set_posting_time = 1
		sinv.posting_date = sales_inv_date
		sinv.save().submit()

		# create credit note on next month start date
		cr_note = make_sales_return(sinv.name)
		cr_note.set_posting_time = 1
		cr_note.posting_date = return_inv_date
		cr_note.save().submit()

		# apply filters for invoiced period
		filters = frappe._dict(
			company=self.company, from_date=month_start_date, to_date=month_start_date, group_by="Invoice"
		)

		_, data = execute(filters=filters)
		total = data[-1]

		self.assertEqual(total.selling_amount, 200.0)
		self.assertEqual(total.buying_amount, 100.0)
		self.assertEqual(total.gross_profit, 100.0)
		self.assertEqual(total.get("gross_profit_%"), 50.0)

		# extend filters upto returned period
		filters.update({"to_date": return_inv_date})

		_, data = execute(filters=filters)
		total = data[-1]

		self.assertEqual(total.selling_amount, 0.0)
		self.assertEqual(total.buying_amount, 0.0)
		self.assertEqual(total.gross_profit, 0.0)
		self.assertEqual(total.get("gross_profit_%"), 0.0)

		# apply filters only on returned period
		filters.update({"from_date": return_inv_date, "to_date": return_inv_date})
		_, data = execute(filters=filters)
		total = data[-1]

		self.assertEqual(total.selling_amount, -200.0)
		self.assertEqual(total.buying_amount, -100.0)
		self.assertEqual(total.gross_profit, -100.0)
		self.assertEqual(total.get("gross_profit_%"), -50.0)

	def test_sales_person_wise_gross_profit(self):
		sales_person = make_sales_person("_Test Sales Person")

		posting_date = get_first_day(nowdate())
		qty = 10
		rate = 100

		sinv = self.create_sales_invoice(qty=qty, rate=rate, do_not_save=True, do_not_submit=True)
		sinv.set_posting_time = 1
		sinv.posting_date = posting_date
		sinv.append(
			"sales_team",
			{
				"sales_person": sales_person.name,
				"allocated_percentage": 100,
				"allocated_amount": 1000.0,
				"commission_rate": 5,
				"incentives": 5,
			},
		)
		sinv.save().submit()

		filters = frappe._dict(
			company=self.company, from_date=posting_date, to_date=posting_date, group_by="Sales Person"
		)

		_, data = execute(filters=filters)
		total = data[-1]

		self.assertEqual(total[5], 1000.0)  # selling amount
		self.assertEqual(total[6], 1000.0)  # buying amount
		self.assertEqual(total[7], 0.0)  # gross profit
		self.assertEqual(total[8], 0.0)  # gross profit %

	def test_drop_ship(self):
		from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice

		so = self.create_drop_ship_order()
		si = make_sales_invoice(so.name).submit()

		filters = frappe._dict(
			company=si.company, from_date=si.posting_date, to_date=si.posting_date, group_by="Invoice"
		)

		_, data = execute(filters=filters)
		self.assertEqual(data[1].buying_amount, 800)
		self.assertIsNone(data[1].buying_rate)
		self.assertEqual(data[1]["gross_profit_%"], 20)

	def test_drop_ship_partial_billing_and_return(self):
		from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice

		so = self.create_drop_ship_order()
		first_invoice = make_sales_invoice(so.name)
		first_invoice.items[0].qty = 4
		first_invoice.submit()
		second_invoice = make_sales_invoice(so.name).submit()

		filters = frappe._dict(
			company=first_invoice.company,
			from_date=first_invoice.posting_date,
			to_date=first_invoice.posting_date,
			group_by="Invoice",
		)
		_, data = execute(filters=filters)
		invoice_rows = {
			row.parent_invoice: row
			for row in data
			if row.parent_invoice in {first_invoice.name, second_invoice.name} and row.indent == 1
		}
		self.assertEqual(invoice_rows[first_invoice.name].buying_amount, 320)
		self.assertEqual(invoice_rows[second_invoice.name].buying_amount, 480)

		sales_return = make_sales_return(first_invoice.name)
		sales_return.items[0].qty = -2
		sales_return.submit()

		_, data = execute(filters=filters)
		first_invoice_row = next(
			row for row in data if row.parent_invoice == first_invoice.name and row.indent == 1
		)
		self.assertEqual(first_invoice_row.qty, 2)
		self.assertEqual(first_invoice_row.buying_amount, 160)
		self.assertEqual(first_invoice_row.gross_profit, 40)

	def test_drop_ship_return_matches_sales_invoice_item(self):
		from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice
		from erpnext.selling.doctype.sales_order.mapper import make_purchase_order, make_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(
			"_Test Drop Ship Consolidated Return Item",
			properties={"is_stock_item": 1, "delivered_by_supplier": 1},
		)
		sales_orders = []
		for qty, selling_rate, buying_rate in [(4, 100, 50), (6, 200, 80)]:
			sales_order = make_sales_order(item=item.name, qty=qty, rate=selling_rate, do_not_submit=True)
			sales_order.items[0].delivered_by_supplier = 1
			sales_order.items[0].supplier = "_Test Supplier"
			sales_order.submit()
			sales_orders.append(sales_order)

			purchase_order = make_purchase_order(sales_order.name, selected_items=[sales_order.items[0]])[0]
			purchase_order.items[0].rate = buying_rate
			purchase_order.supplier = "_Test Supplier"
			purchase_order.submit()
			make_purchase_invoice(purchase_order.name).submit()

		sales_invoice = make_sales_invoice(sales_orders[0].name)
		sales_invoice = make_sales_invoice(sales_orders[1].name, target_doc=sales_invoice).submit()
		sales_return = make_sales_return(sales_invoice.name)
		sales_return.set("items", [sales_return.items[0]])
		sales_return.items[0].qty = -1
		sales_return.submit()

		filters = frappe._dict(
			company=sales_invoice.company,
			from_date=sales_invoice.posting_date,
			to_date=sales_invoice.posting_date,
			group_by="Invoice",
		)
		_, data = execute(filters=filters)
		invoice_rows = [row for row in data if row.parent_invoice == sales_invoice.name and row.indent == 1]
		invoice_rows.sort(key=lambda row: row["avg._selling_rate"])
		self.assertEqual([row.qty for row in invoice_rows], [3, 6])
		self.assertEqual([row.buying_amount for row in invoice_rows], [150, 480])

	def test_return_matches_sales_invoice_item_for_delivery_note(self):
		make_stock_entry(
			company=self.company,
			item_code=self.item,
			target=self.warehouse,
			qty=4,
			basic_rate=50,
		)
		delivery_note = self.create_delivery_note(qty=4, rate=100)
		sales_invoice = make_sales_invoice(delivery_note.name).submit()
		sales_return = make_sales_return(sales_invoice.name)
		sales_return.items[0].qty = -1
		sales_return.submit()

		filters = frappe._dict(
			company=sales_invoice.company,
			from_date=sales_invoice.posting_date,
			to_date=sales_invoice.posting_date,
			group_by="Invoice",
		)
		_, data = execute(filters=filters)
		invoice_row = next(
			row for row in data if row.parent_invoice == sales_invoice.name and row.indent == 1
		)
		self.assertEqual(invoice_row.qty, 3)
		self.assertEqual(invoice_row.selling_amount, 300)

	def test_return_combines_linked_and_legacy_item_buckets(self):
		sales_invoice = self.create_sales_invoice(qty=4, rate=100)
		linked_return = make_sales_return(sales_invoice.name)
		linked_return.items[0].qty = -1
		linked_return.submit()

		legacy_return = make_sales_return(sales_invoice.name)
		legacy_return.items[0].qty = -1
		legacy_return.submit()
		frappe.db.set_value("Sales Invoice Item", legacy_return.items[0].name, "sales_invoice_item", None)

		filters = frappe._dict(
			company=sales_invoice.company,
			from_date=sales_invoice.posting_date,
			to_date=sales_invoice.posting_date,
			group_by="Invoice",
		)
		_, data = execute(filters=filters)
		invoice_row = next(
			row for row in data if row.parent_invoice == sales_invoice.name and row.indent == 1
		)
		self.assertEqual(invoice_row.qty, 2)
		self.assertEqual(invoice_row.selling_amount, 200)

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": True})
	def test_legacy_return_prefers_item_without_linked_return(self):
		sales_invoice = self.create_sales_invoice(qty=2, rate=100, do_not_submit=True)
		second_item = frappe.copy_doc(sales_invoice.items[0], ignore_no_copy=False)
		second_item.rate = 200
		sales_invoice.append("items", second_item)
		sales_invoice.submit()

		linked_return = make_sales_return(sales_invoice.name)
		linked_return.set("items", [linked_return.items[0]])
		linked_return.items[0].qty = -1
		linked_return.submit()

		legacy_return = make_sales_return(sales_invoice.name)
		legacy_return.set("items", [legacy_return.items[1]])
		legacy_return.items[0].qty = -1
		legacy_return.submit()
		frappe.db.set_value("Sales Invoice Item", legacy_return.items[0].name, "sales_invoice_item", None)

		filters = frappe._dict(
			company=sales_invoice.company,
			from_date=sales_invoice.posting_date,
			to_date=sales_invoice.posting_date,
			group_by="Invoice",
		)
		_, data = execute(filters=filters)
		invoice_rows = [row for row in data if row.parent_invoice == sales_invoice.name and row.indent == 1]
		invoice_rows.sort(key=lambda row: row["avg._selling_rate"])
		self.assertEqual([row.qty for row in invoice_rows], [1, 1])
		self.assertEqual([row.selling_amount for row in invoice_rows], [100, 200])

	def test_legacy_return_remainder_spills_into_linked_item(self):
		invoice = "SINV-TEST-RETURN-ALLOCATION"
		linked_item = "SINV-ITEM-LINKED"
		unlinked_item = "SINV-ITEM-LEGACY"
		generator = GrossProfitGenerator.__new__(GrossProfitGenerator)
		generator.currency_precision = 3
		generator.filters = frappe._dict(group_by="Invoice")
		generator.returned_invoices = frappe._dict(
			{invoice: frappe._dict({linked_item: [frappe._dict(qty=-1, base_amount=-100)]})}
		)
		generator.legacy_returned_invoices = frappe._dict(
			{invoice: frappe._dict({self.item: [frappe._dict(qty=-2, base_amount=-200)]})}
		)
		linked_row = frappe._dict(
			parent=invoice,
			item_code=self.item,
			item_row=linked_item,
			is_return=False,
			qty=3,
			base_amount=300,
			buying_rate=50,
			delivered_by_supplier=False,
		)
		unlinked_row = frappe._dict(
			parent=invoice,
			item_code=self.item,
			item_row=unlinked_item,
			is_return=False,
			qty=1,
			base_amount=100,
			buying_rate=50,
			delivered_by_supplier=False,
		)

		generator.si_list = [unlinked_row, linked_row]
		generator.allocate_legacy_return_items()
		generator.update_return_invoices(linked_row, linked_item)
		generator.update_return_invoices(unlinked_row, unlinked_item)

		self.assertEqual((linked_row.qty, linked_row.base_amount), (1, 100))
		self.assertEqual((unlinked_row.qty, unlinked_row.base_amount), (0, 0))

	def test_legacy_return_ignores_skipped_group_rows(self):
		invoice = "SINV-TEST-SKIPPED-RETURN-ALLOCATION"
		visible_item = "SINV-ITEM-WITH-PROJECT"
		skipped_item = "SINV-ITEM-WITHOUT-PROJECT"
		generator = GrossProfitGenerator.__new__(GrossProfitGenerator)
		generator.currency_precision = 3
		generator.filters = frappe._dict(group_by="Project")
		generator.returned_invoices = frappe._dict(
			{invoice: frappe._dict({visible_item: [frappe._dict(qty=-1, base_amount=-100)]})}
		)
		generator.legacy_returned_invoices = frappe._dict(
			{invoice: frappe._dict({self.item: [frappe._dict(qty=-1, base_amount=-100)]})}
		)
		visible_row = frappe._dict(
			parent=invoice,
			item_code=self.item,
			item_row=visible_item,
			is_return=False,
			project="_Test Project",
			qty=2,
			base_amount=200,
			buying_rate=50,
			delivered_by_supplier=False,
		)
		skipped_row = frappe._dict(
			parent=invoice,
			item_code=self.item,
			item_row=skipped_item,
			is_return=False,
			project=None,
			qty=1,
		)

		generator.si_list = [visible_row, skipped_row]
		generator.allocate_legacy_return_items()
		generator.update_return_invoices(visible_row, visible_item)

		self.assertNotIn(skipped_item, generator.returned_invoices[invoice])
		self.assertEqual((visible_row.qty, visible_row.base_amount), (0, 0))

	def test_monthly_group_allocates_legacy_return(self):
		invoice = "SINV-TEST-MONTHLY-RETURN-ALLOCATION"
		item_row = "SINV-ITEM-MONTHLY-RETURN"
		generator = GrossProfitGenerator.__new__(GrossProfitGenerator)
		generator.currency_precision = 3
		generator.filters = frappe._dict(group_by="Monthly")
		generator.returned_invoices = frappe._dict()
		generator.legacy_returned_invoices = frappe._dict(
			{invoice: frappe._dict({self.item: [frappe._dict(qty=-1, base_amount=-100)]})}
		)
		invoice_row = frappe._dict(
			parent=invoice,
			item_code=self.item,
			item_row=item_row,
			is_return=False,
			posting_date=nowdate(),
			qty=1,
			base_amount=100,
			buying_rate=50,
			delivered_by_supplier=False,
		)

		generator.si_list = [invoice_row]
		generator.allocate_legacy_return_items()
		generator.update_return_invoices(invoice_row, item_row)

		self.assertEqual((invoice_row.qty, invoice_row.base_amount), (0, 0))

	def test_return_remainder_stays_available_for_next_row(self):
		invoice = "SINV-TEST-RETURN-REMAINDER"
		item_row = "SINV-ITEM-RETURN-REMAINDER"
		returned_item = frappe._dict(qty=-2, base_amount=-200)
		generator = GrossProfitGenerator.__new__(GrossProfitGenerator)
		generator.currency_precision = 3
		generator.returned_invoices = frappe._dict({invoice: frappe._dict({item_row: [returned_item]})})
		first_row = frappe._dict(
			parent=invoice,
			item_code=self.item,
			qty=1,
			base_amount=100,
			buying_rate=50,
			delivered_by_supplier=False,
		)
		second_row = first_row.copy()

		generator.update_return_invoices(first_row, item_row)
		self.assertEqual((returned_item.qty, returned_item.base_amount), (-1, -100))

		generator.update_return_invoices(second_row, item_row)
		self.assertEqual((returned_item.qty, returned_item.base_amount), (0, 0))
		self.assertEqual((first_row.qty, second_row.qty), (0, 0))

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": True})
	def test_return_keeps_buying_amount_of_unreturned_row(self):
		unreturned_item = create_item(
			"_Test Gross Profit Unreturned Item", warehouse=self.warehouse, company=self.company
		)
		make_stock_entry(
			company=self.company,
			item_code=unreturned_item.name,
			target=self.warehouse,
			qty=40000,
			basic_rate=33.33333,
		)
		sales_invoice = self.create_sales_invoice(qty=1, rate=100, do_not_submit=True)
		second_item = frappe.copy_doc(sales_invoice.items[0], ignore_no_copy=False)
		second_item.item_code = unreturned_item.name
		second_item.item_name = unreturned_item.name
		second_item.qty = 30000
		sales_invoice.append("items", second_item)
		sales_invoice.submit()

		sales_return = make_sales_return(sales_invoice.name)
		sales_return.set("items", [sales_return.items[0]])
		sales_return.items[0].qty = -1
		sales_return.submit()

		filters = frappe._dict(
			company=sales_invoice.company,
			from_date=sales_invoice.posting_date,
			to_date=sales_invoice.posting_date,
			group_by="Invoice",
		)
		_, data = execute(filters=filters)
		invoice_row = next(
			row
			for row in data
			if row.parent_invoice == sales_invoice.name and row.item_code == unreturned_item.name
		)
		self.assertEqual(invoice_row.qty, 30000)
		self.assertEqual(invoice_row.buying_amount, 999999.9)

	def create_drop_ship_order(self, qty=10, selling_rate=100, buying_rate=80):
		from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice
		from erpnext.selling.doctype.sales_order.mapper import make_purchase_order
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item("_Test Drop Ship Item", properties={"is_stock_item": 1, "delivered_by_supplier": 1})
		so = make_sales_order(item=item.name, qty=qty, rate=selling_rate)
		purchase_order = make_purchase_order(so.name, selected_items=[so.items[0]])[0]
		purchase_order.items[0].rate = buying_rate
		purchase_order.supplier = "_Test Supplier"
		purchase_order.submit()
		make_purchase_invoice(purchase_order.name).submit()

		return so

	def create_rate_adjustment_debit_note(self, against_invoice, adjustment_rate, item_code=None):
		"""Create a rate adjustment debit note with no stock movement."""
		dn = self.create_sales_invoice(qty=1, rate=adjustment_rate, do_not_save=True, do_not_submit=True)
		if item_code:
			dn.items[0].item_code = item_code
			dn.items[0].item_name = item_code
		dn.is_debit_note = 1
		dn.return_against = against_invoice.name
		dn.items[0].allow_zero_valuation_rate = 1
		return dn.save().submit()

	def test_debit_note_has_zero_buying_amount_and_full_gross_profit(self):
		"""
		Rate adjustment debit note (is_debit_note=1) should show buying_amount=0
		since there is no stock movement. Gross profit equals the adjustment amount
		and gross profit % equals 100%.
		"""
		make_stock_entry(
			company=self.company,
			item_code=self.item,
			target=self.warehouse,
			qty=1,
			basic_rate=100,
		)

		sinv = self.create_sales_invoice(qty=1, rate=200, do_not_submit=True)
		sinv.update_stock = 1
		sinv = sinv.save().submit()

		debit_note = self.create_rate_adjustment_debit_note(sinv, adjustment_rate=20)

		filters = frappe._dict(
			company=self.company,
			from_date=nowdate(),
			to_date=nowdate(),
			group_by="Invoice",
		)

		columns, data = execute(filters=filters)

		dn_item_rows = [
			x for x in data if x.get("parent_invoice") == debit_note.name and x.get("indent") == 1.0
		]
		self.assertEqual(len(dn_item_rows), 1)

		dn_row = dn_item_rows[0]
		self.assertEqual(dn_row.buying_amount, 0.0)
		self.assertEqual(dn_row.selling_amount, 20.0)
		self.assertEqual(dn_row.gross_profit, 20.0)
		self.assertEqual(dn_row["gross_profit_%"], 100.0)

	def test_original_invoice_unaffected_by_rate_adjustment_debit_note(self):
		"""
		The original invoice's GP should be derived solely from its own selling
		amount and COGS — the rate adjustment debit note must not alter it.
		"""
		make_stock_entry(
			company=self.company,
			item_code=self.item,
			target=self.warehouse,
			qty=1,
			basic_rate=100,
		)

		sinv = self.create_sales_invoice(qty=1, rate=200, do_not_submit=True)
		sinv.update_stock = 1
		sinv = sinv.save().submit()

		self.create_rate_adjustment_debit_note(sinv, adjustment_rate=20)

		filters = frappe._dict(
			company=self.company,
			from_date=nowdate(),
			to_date=nowdate(),
			group_by="Invoice",
		)

		columns, data = execute(filters=filters)

		sinv_item_rows = [x for x in data if x.get("parent_invoice") == sinv.name and x.get("indent") == 1.0]
		self.assertEqual(len(sinv_item_rows), 1)

		sinv_row = sinv_item_rows[0]
		self.assertEqual(sinv_row.selling_amount, 200.0)
		self.assertEqual(sinv_row.buying_amount, 100.0)
		self.assertEqual(sinv_row.gross_profit, 100.0)
		self.assertEqual(sinv_row["gross_profit_%"], 50.0)

	def test_debit_note_qty_not_inflated_in_grouped_report(self):
		"""
		When grouped by Item Code, the debit note (qty=0) must not inflate
		the group's qty or buying_amount. The selling amount and average
		selling rate correctly reflect the rate adjustment.
		"""
		item = create_item("_Test Rate Adjustment Debit Note Item")

		make_stock_entry(
			company=self.company,
			item_code=item.item_code,
			target=self.warehouse,
			qty=1,
			basic_rate=100,
		)

		sinv = create_sales_invoice(
			qty=1,
			rate=200,
			company=self.company,
			customer=self.customer,
			item_code=item.item_code,
			item_name=item.item_code,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			update_stock=1,
			currency="INR",
			income_account=self.income_account,
			expense_account=self.expense_account,
		)

		self.create_rate_adjustment_debit_note(sinv, adjustment_rate=20, item_code=item.item_code)

		filters = frappe._dict(
			company=self.company,
			from_date=nowdate(),
			to_date=nowdate(),
			group_by="Item Code",
		)

		columns, data = execute(filters=filters)

		# group_by="Item Code" column order:
		# [item_code, item_name, brand, description, qty, base_rate,
		#  buying_rate, base_amount, buying_amount, gross_profit, gross_profit_percent, currency]
		item_row = next((row for row in data if row[0] == item.item_code), None)
		self.assertIsNotNone(item_row)

		qty, base_rate, buying_amount, base_amount, gross_profit, gp_percent = (
			item_row[4],
			item_row[5],
			item_row[8],
			item_row[7],
			item_row[9],
			item_row[10],
		)

		self.assertEqual(qty, 1.0)  # debit note adds qty=0, not inflated
		self.assertEqual(buying_amount, 100.0)  # only original invoice COGS
		self.assertEqual(base_amount, 220.0)  # 200 (original) + 20 (adjustment)
		self.assertEqual(base_rate, 220.0)  # avg selling rate = 220/1
		self.assertEqual(gross_profit, 120.0)  # 220 - 100
		self.assertAlmostEqual(gp_percent, 54.545, places=2)  # 120/220 * 100


def make_sales_person(sales_person_name="_Test Sales Person"):
	if not frappe.db.exists("Sales Person", {"sales_person_name": sales_person_name}):
		sales_person_doc = frappe.get_doc(
			{
				"doctype": "Sales Person",
				"is_group": 0,
				"parent_sales_person": "Sales Team",
				"sales_person_name": sales_person_name,
			}
		).insert(ignore_permissions=True)
	else:
		sales_person_doc = frappe.get_doc("Sales Person", {"sales_person_name": sales_person_name})

	return sales_person_doc
