# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime
from erpnext.accounts.utils import get_account_currency
from erpnext.stock.utils import get_incoming_rate
from frappe.utils import flt

class InventoryAdjustment(Document):
	def validate(self):
		if self.docstatus == 0:
			for item in self.get("items"):
				self.args = self.get_args_for_incoming_rate(item)
			self.set_incoming_rate()

		if self.docstatus == 1:
			stock_type = frappe.get_doc("Stock Entry Type", self.stock_entry_type)
			if stock_type.accounting_seat == 1:
				amount_total_debit = 0
				amount_total_credit = 0
				for item in self.get("items"):
					items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})
					actual_qty = 0
					basic_amount = 0
					for bin in items_bin:
						if self.from_warehouse == bin.warehouse:
							doc = frappe.get_doc("Bin", bin.name)
							actual_qty = item.qty - doc.actual_qty
							self.create_stock_ledger_entry(item, doc.actual_qty, 0)
					if item.basic_rate == 0:
						it = frappe.get_doc("Item", item.item_code)
						basic_amount += it.valuation_rate * actual_qty
					else:
						basic_amount = item.basic_rate * actual_qty

					if basic_amount != 0:
						if basic_amount > 0:
							self.apply_gl_entry_items(item, basic_amount)
						else:
							self.apply_gl_entry_items_debit(item, basic_amount)
					else:
						amount_total_debit += item.basic_amount * item.qty							
						if basic_amount > 0:
							self.apply_gl_entry_items(item, amount_total_debit)	
						else:
							self.apply_gl_entry_items_debit(item, amount_total_debit)		
					
					# if actual_qty > 0:
					# 	amount_total_debit += basic_amount
					# else:
					# 	amount_total_credit += basic_amount
				
				# if amount_total_debit != 0:
				# 	self.apply_gl_entry_type(amount_total_debit, 0)
				
				# if amount_total_credit != 0:
				# 	self.apply_gl_entry_type(amount_total_credit, 1)
	def on_update(self):
		if self.docstatus == 0:
			self.calculate_total()
	
	def get_args_for_incoming_rate(self, item):
		return frappe._dict({
			"item_code": item.item_code,
			"warehouse": self.from_warehouse,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			"qty": item.qty,
			"serial_no": item.serial_no,
			"voucher_type": self.doctype,
			"voucher_no": item.name,
			"company": self.company,
			"allow_zero_valuation": item.allow_zero_valuation_rate,
		})

	def calculate_total(self):
		total = 0
		for item in self.get("items"):
			items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})
			for bin in items_bin:
				if self.from_warehouse == bin.warehouse:
					if item.basic_rate == 0:
						it = frappe.get_doc("Item", item.item_code)
						total += it.valuation_rate * item.qty
					else:
						total += item.basic_rate * item.qty

		self.total_amount = total

	def create_stock_ledger_entry(self, item, qty, delete, allow_negative_stock=False, via_landed_cost_voucher=False, is_amended=None):
		qty_item = 0

		if delete == 1:
			qty_item = item.qty - (item.qty * 2)
		else:
			qty_item = item.qty

		actual_qty = qty * -1

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
			"warehouse": self.from_warehouse,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			'fiscal_year': fiscal_year[0].name,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"voucher_detail_no": self.name,
			"actual_qty": actual_qty,
			"stock_uom": frappe.db.get_value("Item", item.item_code or item.item_code, "stock_uom"),
			"incoming_rate": 0,
			"company": self.company,
			"batch_no": None,
			"serial_no": None,
			"valuation_rate": None,
			"project": None,
			"is_cancelled": self.docstatus==2 and "Yes" or "No",
			'doctype':self.doctype
		})

		sle_id = make_entry(sle, allow_negative_stock, via_landed_cost_voucher)

		sle.update({
			"sle_id": sle_id,
			"is_amended": is_amended
		})

		sle = ({
			"item_code": item.item_code,
			"warehouse": self.from_warehouse,
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
			"batch_no": None,
			"serial_no": None,
			"valuation_rate": None,
			"project": None,
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
	
	def apply_gl_entry_items(self, item, basic_amount):
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
		
		if item.inventory_default_values == None:
			inventory_default_values = company.default_expense_account
		else:
			inventory_default_values = item.inventory_default_values
		
		account_currency = get_account_currency(sales_default_values)

		against = frappe.get_doc("Stock Entry Type", self.stock_entry_type)

		account_against = frappe.get_value("Mode of Payment Account", {"parent":against.name, "company": self.company}, "default_account")

		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.posting_date
		doc.transaction_date = self.posting_date
		doc.account = inventory_default_values
		doc.party_type = None
		doc.party = None
		doc.cost_center = company.round_off_cost_center
		doc.debit = 0
		doc.credit = basic_amount
		doc.account_currency = account_currency
		doc.debit_in_account_currency = 0
		doc.credit_in_account_currency = basic_amount
		doc.against = account_against
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

		account_currency = get_account_currency(account_against)
		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.posting_date
		doc.transaction_date = self.posting_date
		doc.account = account_against
		doc.party_type = None
		doc.party = None
		doc.cost_center = company.round_off_cost_center
		doc.debit = basic_amount
		doc.credit = 0
		doc.account_currency = account_currency
		doc.debit_in_account_currency = basic_amount
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
	
	def apply_gl_entry_items_debit(self, item, basic_amount):
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
		
		if item.inventory_default_values == None:
			inventory_default_values = company.default_expense_account
		else:
			inventory_default_values = item.inventory_default_values
		
		account_currency = get_account_currency(sales_default_values)

		against = frappe.get_doc("Stock Entry Type", self.stock_entry_type)

		account_against = frappe.get_value("Mode of Payment Account", {"parent":against.name, "company": self.company}, "default_account")

		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.posting_date
		doc.transaction_date = self.posting_date
		doc.account = inventory_default_values
		doc.party_type = None
		doc.party = None
		doc.cost_center = company.round_off_cost_center
		doc.debit = basic_amount * -1
		doc.credit = 0
		doc.account_currency = account_currency
		doc.debit_in_account_currency = basic_amount * -1
		doc.credit_in_account_currency = 0
		doc.against = account_against
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

		account_currency = get_account_currency(account_against)
		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.posting_date
		doc.transaction_date = self.posting_date
		doc.account = account_against
		doc.party_type = None
		doc.party = None
		doc.cost_center = company.round_off_cost_center
		doc.debit = 0
		doc.credit = basic_amount * -1
		doc.account_currency = account_currency
		doc.debit_in_account_currency = 0
		doc.credit_in_account_currency = basic_amount * -1
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
	
	def set_incoming_rate(self):
		for d in self.get("items"):
			if self.from_warehouse:
				args = self.get_args_for_incoming_rate(d)
				d.basic_rate = get_incoming_rate(args)
	
def make_entry(args, allow_negative_stock=False, via_landed_cost_voucher=False):
	args.update({"doctype": "Stock Ledger Entry"})
	sle = frappe.get_doc(args)
	sle.flags.ignore_permissions = 1
	sle.allow_negative_stock=allow_negative_stock
	sle.via_landed_cost_voucher = via_landed_cost_voucher
	sle.insert()
	sle.submit()
	return sle.name