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
		company_name = "_Test Gross Profit"
		abbr = "_GP"
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
			"avg._selling_rate": 0.0,
			"valuation_rate": 0.0,
			"selling_amount": -100.0,
			"buying_amount": 0.0,
			"gross_profit": -100.0,
			"gross_profit_%": 100.0,
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
