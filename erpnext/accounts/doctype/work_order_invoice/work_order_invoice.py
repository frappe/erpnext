# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime
from erpnext.accounts.utils import get_account_currency

class WorkOrderInvoice(Document):
	def validate(self):
		if self.sales_invoice != None:
			self.delete_items()
			self.add_items()
		
		if self.docstatus == 1:
			# if self.project == None:
			# 	frappe.throw(_("Project is required."))
			
			if self.warehouse == None:
				frappe.throw(_("Warehouse is required."))

			for item in self.get("detail_one"):
				items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})

				for bin in items_bin:
					if self.warehouse == bin.warehouse:
						doc = frappe.get_doc("Bin", bin.name)
						self.create_stock_ledger_entry(item, doc.actual_qty, 0)
						self.apply_gl_entry(item)
			
			for item in self.get("detail_two"):
				items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})

				for bin in items_bin:
					if self.warehouse == bin.warehouse:
						doc = frappe.get_doc("Bin", bin.name)
						self.create_stock_ledger_entry(item, doc.actual_qty, 0)
						self.apply_gl_entry(item)
	
	def on_cancel(self):
		frappe.throw(_("Unable to cancel inventory downloads"))
		for item in self.get("detail_one"):
				items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})

				for bin in items_bin:
					if self.warehouse == bin.warehouse:
						doc = frappe.get_doc("Bin", bin.name)
						self.create_stock_ledger_entry(item, doc.actual_qty, 1)
						
		for item in self.get("detail_two"):
				items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})

				for bin in items_bin:
					if self.warehouse == bin.warehouse:
						doc = frappe.get_doc("Bin", bin.name)
						self.create_stock_ledger_entry(item, doc.actual_qty, 1)

	def delete_items(self):
		items = frappe.get_all("Work Order Items", ["*"], filters = {"parent": self.name})

		for item in items:
			frappe.delete_doc("Work Order Items", item.name)
	
	def add_items(self):
		items = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": self.sales_invoice})
		invoice = frappe.get_doc("Sales Invoice", self.sales_invoice)

		for item in items:
			it = frappe.get_doc("Item", item.item_code)
			if it.is_work_order == 1:
				row = self.append("items", {})
				row.item_code = item.item_code
				row.item_name = item.item_name
				row.qty = item.qty

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
		
		sle = ({
			"item_code": item.item_code,
			"warehouse": self.warehouse,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			'fiscal_year': fiscal_year[0].name,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"voucher_detail_no": self.name,
			"actual_qty": -1*qty_item,
			"stock_uom": frappe.db.get_value("Item", item.item_code or item.item_code, "stock_uom"),
			"incoming_rate": 0,
			"company": self.company,
			"batch_no": None,
			"serial_no": None,
			"valuation_rate": None,
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

	def apply_gl_entry(self, item):
		currentDateTime = datetime.now()
		date = currentDateTime.date()
		year = date.strftime("%Y")

		fecha_inicial = '01-01-{}'.format(year)
		fecha_final = '31-12-{}'.format(year)
		fecha_i = datetime.strptime(fecha_inicial, '%d-%m-%Y')
		fecha_f = datetime.strptime(fecha_final, '%d-%m-%Y')

		fiscal_year = frappe.get_all("Fiscal Year", ["*"], filters = {"year_start_date": [">=", fecha_i], "year_end_date": ["<=", fecha_f]})
		sales_default_values = None
		company = frappe.get_doc("Company", self.company)
		if item.sales_default_values == None:
			sales_default_values = company.default_inventory_account
		else:
			sales_default_values =  item.sales_default_values
		
		inventory_default_values = None
		
		if item.inventory_default_values == None:
			inventory_default_values = company.default_expense_account
		else:
			inventory_default_values = item.inventory_default_values

		price = self.set_valuation_rate(item)

		amount = price * item.qty
		
		account_currency = get_account_currency(sales_default_values)
		
		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.posting_date
		doc.transaction_date = None
		doc.account = sales_default_values
		doc.party_type = "Customer"
		doc.party = self.customer
		doc.cost_center = company.round_off_cost_center
		doc.debit = amount
		doc.credit = 0
		doc.account_currency = account_currency
		doc.debit_in_account_currency = amount
		doc.credit_in_account_currency = 0
		doc.against = inventory_default_values
		doc.against_voucher_type = self.doctype
		doc.against_voucher = self.name
		doc.voucher_type =  self.doctype
		doc.voucher_no = self.name
		doc.voucher_detail_no = None
		doc.project = None
		doc.remarks = 'No Remarks'
		doc.is_opening = "No"
		doc.is_advance = "No"
		doc.fiscal_year = fiscal_year[0].name
		doc.company = self.company
		doc.finance_book = None
		doc.to_rename = 1
		doc.due_date = None
		# doc.docstatus = 1
		doc.insert()

		account_currency = get_account_currency(inventory_default_values)

		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.posting_date
		doc.transaction_date = None
		doc.account = inventory_default_values
		doc.party_type = "Customer"
		doc.party = self.customer
		doc.cost_center = company.round_off_cost_center
		doc.debit = 0
		doc.credit = amount
		doc.account_currency = account_currency
		doc.debit_in_account_currency = 0
		doc.credit_in_account_currency = amount
		doc.against = sales_default_values
		doc.against_voucher_type = self.doctype
		doc.against_voucher = self.name
		doc.voucher_type =  self.doctype
		doc.voucher_no = self.name
		doc.voucher_detail_no = None
		doc.project = None
		doc.remarks = 'No Remarks'
		doc.is_opening = "No"
		doc.is_advance = "No"
		doc.fiscal_year = fiscal_year[0].name
		doc.company = self.company
		doc.finance_book = None
		doc.to_rename = 1
		doc.due_date = None
		# doc.docstatus = 1
		doc.insert()
	
	def set_valuation_rate(self, item):
		valuation_rate = 0

		stock = frappe.get_all("Stock Ledger Entry", ["valuation_rate"], filters = {"item_code": item.item_code})

		if len(stock) > 0:
			valuation_rate += stock[0].valuation_rate
		else:
			frappe.throw(_("The Item {} is not defined valuation rate.".format(item.item_code)))
		
		return valuation_rate

def make_entry(args, allow_negative_stock=False, via_landed_cost_voucher=False):
		args.update({"doctype": "Stock Ledger Entry"})
		sle = frappe.get_doc(args)
		sle.flags.ignore_permissions = 1
		sle.allow_negative_stock=allow_negative_stock
		sle.via_landed_cost_voucher = via_landed_cost_voucher
		sle.insert()
		sle.submit()
		return sle.name