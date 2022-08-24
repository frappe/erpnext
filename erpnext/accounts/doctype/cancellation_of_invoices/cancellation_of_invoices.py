# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, timedelta, date
from frappe.model.naming import parse_naming_series
from frappe.utils.data import money_in_words
from frappe.utils import flt

class CancellationOfInvoices(Document):
	def validate(self):
		self.in_words = money_in_words(self.grand_total)
		total_cost = self.get_cost()
		if self.docstatus == 0:
			if self.grand_total > 0:
				items = frappe.get_all("Cancellation Of Invoices Item", ["*"], filters = {"parent": self.name})
				self.delete_items(items)

			self.get_items()

		if self.docstatus == 1:
			self.add_bin()
			# self.delete_gl_entry()
			self.modified_sale_invoice()
			# cost = super(CancellationOfInvoices, self).get_cost()
			self.update_dashboard_customer()
	
	def update_dashboard_customer(self):
		customers = frappe.get_all("Dashboard Customer",["*"], filters = {"customer": self.customer, "company": self.company})

		invoice = frappe.get_doc("Sales Invoice", self.sale_invoice)

		if len(customers) > 0:
			customer = frappe.get_doc("Dashboard Customer", customers[0].name)
			customer.billing_this_year -= invoice.grand_total
			customer.total_unpaid -= invoice.outstanding_amount
			customer.save()
		else:
			new_doc = frappe.new_doc("Dashboard Customer")
			new_doc.customer = self.customer
			new_doc.company = self.company
			new_doc.billing_this_year = invoice.grand_total * -1
			new_doc.total_unpaid = invoice.outstanding_amount * -1
			new_doc.insert()
		
		self.update_accounts_status(invoice)

	def update_accounts_status(self, invoice):
		customer = frappe.get_doc("Customer", self.customer)

		if customer:
			customer.debit -= invoice.grand_total
			customer.remaining_balance -= invoice.grand_total
			customer.save()

	def on_cancel(self):
		frappe.throw(_("Unable to cancel Cancellation Of Invoice"))
		self.delete_stock_ledger_entry()
		# frappe.throw(_("An annulment cannot be canceled."))

	def delete_items(self, items):
		for item in items:
			frappe.delete_doc("Cancellation Of Invoices Item", item.name)

	def add_bin(self):
		items = frappe.get_all("Cancellation Of Invoices Item", ["*"], filters = {"parent": self.name})

		for item in items:
			items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})

			for bin in items_bin:
				if item.warehouse == bin.warehouse:
					doc = frappe.get_doc("Bin", bin.name)
					doc.actual_qty += item.qty
					doc.db_set('actual_qty', doc.actual_qty, update_modified=False)
					self.create_stock_ledger_entry(item, doc.actual_qty, 0)

	def delete_stock_ledger_entry(self):
		stocks = frappe.get_all("Stock Ledger Entry", ["*"], filters = {"voucher_no": self.name})

		for stock in stocks:
			frappe.delete_doc("Stock Ledger Entry", stock.name)
	
	def get_cost(self):
		ledgers = frappe.get_all("Stock Ledger Entry", ["*"], filters ={"voucher_type": "Sales Invoice", "voucher_no": self.sale_invoice})

		total_cost = 0

		for ledger in ledgers:
			total_cost += flt(ledger.stock_value_difference, 2)
		
		return total_cost

	def set_valuation_rate(self, item):		
		stock = frappe.get_all("Stock Ledger Entry", ["*"], filters = {"item_code": item.item_code})

		if len(stock) == 0:
			valuation_rate = 0
		else:
			valuation_rate = stock[0].valuation_rate
			
		return valuation_rate

	def create_stock_ledger_entry(self, item, qty, delete, allow_negative_stock=False, via_landed_cost_voucher=False, is_amended=None):
		qty_item = 0

		if delete == 1:
			qty_item = item.qty - (item.qty * 2)
		else:
			qty_item = item.qty

		currentDateTime = datetime.now()
		date = currentDateTime.date()
		year = date.strftime("%Y")

		fecha_inicial = '01-01-{}'.format(year)
		fecha_final = '31-12-{}'.format(year)
		fecha_i = datetime.strptime(fecha_inicial, '%d-%m-%Y')
		fecha_f = datetime.strptime(fecha_final, '%d-%m-%Y')

		fiscal_year = frappe.get_all("Fiscal Year", ["*"], filters = {"year_start_date": [">=", fecha_i], "year_end_date": ["<=", fecha_f]})

		valuation_rate = self.set_valuation_rate(item)

		sle = ({
			"item_code": item.item_code,
			"warehouse": item.warehouse,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			'fiscal_year': fiscal_year[0].name,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"voucher_detail_no": self.name,
			"actual_qty": qty_item,
			"stock_uom": frappe.db.get_value("Item", item.item_code or item.item_code, "stock_uom"),
			"incoming_rate": 0,
			"company": self.company,
			"batch_no": item.batch_no,
			"serial_no": item.serial_no,
			"valuation_rate": valuation_rate,
			"project": self.project,
			"is_cancelled": self.docstatus==2 and "Yes" or "No",
			'doctype':self.doctype
		})

		sle_id = make_entry(sle, allow_negative_stock, via_landed_cost_voucher)

		sle.update({
			"sle_id": sle_id,
			"is_amended": is_amended
		})

		from erpnext.stock.utils import update_bin

		update_bin(sle, allow_negative_stock, via_landed_cost_voucher)

		# doc.insert()

	def get_items(self):
		items = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": self.sale_invoice})

		for item in items:
			self.set_new_row_item(item)

	def set_new_row_item(self, item):
		row = self.append("items", {})
		row.item_code = item.item_code
		row.qty = item.qty
		row.rate = item.rate
		row.amount = item.amount
		row.parent = self.name
		row.uom = item.uom
		row.description = item.description
		row.item_name = item.item_name
		row.conversion_factor = item.conversion_factor
		row.base_rate = item.base_rate
		row.base_amount = item.base_amount
		row.income_account = item.income_account
		row.cost_center = item.cost_center
		row.tax_detail = item.tax_detail
		row.barcode = item.barcode
		row.category_for_sale = item.category_for_sale
		row.customer_item_code = item.customer_item_code
		row.description_section = item.description_section
		row.item_group = item.item_group
		row.brand = item.brand
		row.image = item.image
		row.image_view = item.image_view
		row.stock_uom = item.stock_uom
		row.stock_qty = item.stock_qty
		row.purchase_rate = item.purchase_rate
		row.price_list_rate = item.price_list_rate
		row.base_price_list_rate = item.base_price_list_rate
		row.discount_and_margin = item.discount_and_margin
		row.discount_reason = item.discount_reason
		row.margin_type = item.margin_type
		row.margin_rate_or_amount = item.margin_rate_or_amount
		row.rate_with_margin = item.rate_with_margin
		row.discount_percentage = item.discount_percentage
		row.discount_amount = item.discount_amount
		row.base_rate_with_margin = item.base_rate_with_margin
		row.item_tax_template = item.item_tax_template
		row.tax_detail = item.tax_detail
		row.pricing_rules = item.pricing_rules
		row.is_free_item = item.is_free_item
		row.net_rate = item.net_rate
		row.net_amount = item.net_amount
		row.base_net_rate = item.base_net_rate
		row.base_net_amount = item.base_net_amount
		row.is_fixed_asset = item.is_fixed_asset
		row.asset = item.asset
		row.finance_book = item.finance_book
		row.expense_account = item.expense_account
		row.deferred_revenue_account = item.deferred_revenue_account
		row.service_stop_date = item.service_stop_date
		row.enable_deferred_revenue = item.enable_deferred_revenue
		row.service_start_date = item.service_start_date
		row.service_end_date = item.service_end_date
		row.weight_per_unit = item.weight_per_unit
		row.total_weight = item.total_weight
		row.weight_uom = item.weight_uom
		row.warehouse = item.warehouse
		row.target_warehouse = item.target_warehouse
		row.quality_inspection = item.quality_inspection
		row.batch_no = item.batch_no
		row.allow_zero_valuation_rate = item.allow_zero_valuation_rate
		row.serial_no = item.serial_no
		row.item_tax_rate = item.item_tax_rate
		row.actual_batch_qty = item.actual_batch_qty
		row.actual_qty = item.actual_qty
		row.edit_references = item.edit_references
		row.sales_order = item.sales_order
		row.so_detail = item.so_detail
		row.delivery_note = item.delivery_note
		row.dn_detail = item.dn_detail
		row.delivered_qty = item.delivered_qty
		row.cost_center = item.cost_center
		row.page_break = item.page_break

	def delete_gl_entry(self):
		entrys = frappe.get_all("GL Entry", ["*"], filters = {"voucher_no": self.sale_invoice})

		for entry in entrys:
			doc = frappe.get_doc("GL Entry", entry.name)
			doc.db_set('docstatus', 0, update_modified=False)

			frappe.delete_doc("GL Entry", entry.name)

	def modified_sale_invoice(self):
		# doc = frappe.get_doc("Sales Invoice", self.sale_invoice)
		# doc.db_set('docstatus', 0, update_modified=False)
		# doc.db_set('status', "Draft", update_modified=False)

		# items = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": self.sale_invoice})

		# for item in items:
		# 	product = frappe.get_doc("Sales Invoice Item", item.name)
		# 	product.db_set('rate', 0, update_modified=False)
		# 	product.db_set('amount', 0, update_modified=False)

		doc = frappe.get_doc("Sales Invoice", self.sale_invoice)
		doc.db_set('status', "Cancelled", update_modified=False)
		doc.db_set('docstatus', 9, update_modified=False)
		# doc.db_set('partial_discount', 0, update_modified=False)
		# doc.db_set('discount_amount', 0, update_modified=False)
		# doc.db_set('base_discount_amount', 0, update_modified=False)
		# doc.db_set('total_qty', 0, update_modified=False)
		# doc.db_set('total', 0, update_modified=False)
		# doc.db_set('total_net_weight', 0, update_modified=False)
		# doc.db_set('total_taxes_and_charges', 0, update_modified=False)
		# doc.db_set('additional_discount_percentage', 0, update_modified=False)
		# doc.db_set('taxed_sales15', 0, update_modified=False)
		# doc.db_set('isv15', 0, update_modified=False)
		# doc.db_set('taxed_sales18', 0, update_modified=False)
		# doc.db_set('isv18', 0, update_modified=False)
		# doc.db_set('total_exempt', 0, update_modified=False)
		# doc.db_set('total_exonerated', 0, update_modified=False)
		# doc.db_set('grand_total', 0, update_modified=False)
		# doc.db_set('rounding_adjustment', 0, update_modified=False)
		# doc.db_set('rounded_total', 0, update_modified=False)
		# doc.db_set('total_advance', 0, update_modified=False)
		# doc.db_set('outstanding_amount', 0, update_modified=False)
		# doc.db_set('paid_amount', 0, update_modified=False)
		# doc.db_set('base_change_amount', 0, update_modified=False)
		# doc.db_set('change_amount', 0, update_modified=False)
		# doc.db_set('write_off_amount', 0, update_modified=False)
		# doc.db_set('commission_rate', 0, update_modified=False)
		# doc.db_set('total_commission', 0, update_modified=False)

def make_entry(args, allow_negative_stock=False, via_landed_cost_voucher=False):
		args.update({"doctype": "Stock Ledger Entry"})
		sle = frappe.get_doc(args)
		sle.flags.ignore_permissions = 1
		sle.allow_negative_stock=allow_negative_stock
		sle.via_landed_cost_voucher = via_landed_cost_voucher
		sle.insert()
		sle.submit()
		return sle.name