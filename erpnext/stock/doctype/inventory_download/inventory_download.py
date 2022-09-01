# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _, throw
from datetime import datetime
from frappe.utils import cint, flt, cstr
from erpnext.accounts.utils import get_account_currency

class InventoryDownload(Document):
	def validate(self):
		if self.docstatus == 1:
			# self.apply_inventory_download()

			for item in self.get("items"):
				items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})

				for bin in items_bin:
					if self.warehouse == bin.warehouse:
						doc = frappe.get_doc("Bin", bin.name)
						self.create_stock_ledger_entry(item, doc.actual_qty, 0)			
						self.apply_gl_entry(item)
	
	def on_update(self):
		if self.docstatus == 0:
			self.set_valuation_rate()
	
	def on_cancel(self):
		frappe.throw(_("Unable to cancel inventory downloads"))
		# self.delete_bin()
		# self.apply_inventory_download_cancel()
		for item in self.get("items"):
				items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})

				for bin in items_bin:
					if self.warehouse == bin.warehouse:
						doc = frappe.get_doc("Bin", bin.name)
						self.create_stock_ledger_entry(item, doc.actual_qty, 1)
		
		# self.delete_stock_ledger_entry()
	
	def apply_inventory_download(self):
		items = frappe.get_all("Inventory Download Detail", ["item_code", "qty"], filters = {"parent": self.name})

		for item in items:
			bin = frappe.get_all("Bin", ["name", "actual_qty"], filters = {"warehouse": self.warehouse, "item_code": item.item_code})

			if len(bin) > 0:
				if bin[0].actual_qty >= item.qty:
					doc = frappe.get_doc("Bin", bin[0].name)
					doc.actual_qty -= item.qty
					doc.projected_qty -= item.qty
					doc.db_set('actual_qty', doc.actual_qty, update_modified=False)
					doc.db_set('projected_qty', doc.projected_qty, update_modified=False)
				else:
					frappe.throw(_("There is not enough quantity to download in stock."))
			else:
				frappe.throw(_("This {} product does not exist in inventory with the selected warehouse.".format(item.item_code)))
	
	def apply_inventory_download_cancel(self):
		items = frappe.get_all("Inventory Download Detail", ["item_code", "qty"], filters = {"parent": self.name})

		for item in items:
			bin = frappe.get_all("Bin", ["name", "actual_qty"], filters = {"warehouse": self.warehouse, "item_code": item.item_code})

			if len(bin) > 0:
				doc = frappe.get_doc("Bin", bin[0].name)
				doc.actual_qty += item.qty
				doc.db_set('actual_qty', doc.actual_qty, update_modified=False)
				doc.save()
			else:
				frappe.throw(_("This product does not exist in inventory with the selected warehouse."))

	def delete_stock_ledger_entry(self):
		stocks = frappe.get_all("Stock Ledger Entry", ["*"], filters = {"voucher_no": self.name})

		for stock in stocks:
			# frappe.delete_doc("Stock Ledger Entry", stock.name)
			frappe.db.sql("Delete FROM `tabStock Ledger Entry` where name=%s", stock.name)
	
	def set_valuation_rate(self):
		valuation_rate = 0

		for item in self.get("items"):
			stock = frappe.get_all("Stock Ledger Entry", ["*"], filters = {"item_code": item.item_code})

			doc = frappe.get_doc("Inventory Download Detail", item.name)
			doc.db_set('valuation_rate', stock[0].valuation_rate, update_modified=False)

			valuation_rate += stock[0].valuation_rate * item.qty
		
		self.total_valuation_rate = valuation_rate
		self.db_set('total_valuation_rate', valuation_rate, update_modified=False)

	def delete_bin(self):
		for item in self.get("items"):
			items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})

			for bin in items_bin:
				if self.warehouse == bin.warehouse:
					doc = frappe.get_doc("Bin", bin.name)
					doc.actual_qty -= item.qty
					doc.db_set('actual_qty', doc.actual_qty, update_modified=False)
					self.create_stock_ledger_entry(item, doc.actual_qty, 1)
	
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
			"posting_date": self.creation_date,
			"posting_time": self.posting_time,
			'fiscal_year': fiscal_year[0].name,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"voucher_detail_no": self.name,
			"actual_qty": -1*qty_item,
			"stock_uom": frappe.db.get_value("Item", item.item_code or item.item_code, "stock_uom"),
			"incoming_rate": 0,
			"company": self.company,
			"batch_no": item.batch_no,
			"serial_no": item.serial_no,
			"valuation_rate": item.valuation_rate,
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
	
	def apply_gl_entry(self, item):
		currentDateTime = datetime.now()
		date = currentDateTime.date()
		year = date.strftime("%Y")

		fecha_inicial = '01-01-{}'.format(year)
		fecha_final = '31-12-{}'.format(year)
		fecha_i = datetime.strptime(fecha_inicial, '%d-%m-%Y')
		fecha_f = datetime.strptime(fecha_final, '%d-%m-%Y')

		fiscal_year = frappe.get_all("Fiscal Year", ["*"], filters = {"year_start_date": [">=", fecha_i], "year_end_date": ["<=", fecha_f]})

		if item.sales_default_values == None:
			frappe.throw(_("Assign an sales default values in item {}.".format(item.item_code)))
			
		if item.inventory_default_values == None:
			frappe.throw(_("Assign an inventory default account in item {}.".format(item.item_code)))

		price = self.set_valuation_rate_item(item)

		amount = price * item.qty

		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.creation_date
		doc.transaction_date = None
		doc.account = item.sales_default_values
		doc.party_type = "Employee"
		doc.party = self.responsable
		doc.cost_center = self.cost_center
		doc.debit = amount
		doc.credit = 0
		doc.account_currency = self.currency
		doc.debit_in_account_currency = amount
		doc.credit_in_account_currency = 0
		doc.against = item.sales_default_values
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

		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.creation_date
		doc.transaction_date = None
		doc.account = item.inventory_default_values
		doc.party_type = "Employee"
		doc.party = self.responsable
		doc.cost_center = self.cost_center
		doc.debit = 0
		doc.credit = amount
		doc.account_currency = self.currency
		doc.debit_in_account_currency = 0
		doc.credit_in_account_currency = amount
		doc.against = item.inventory_default_values
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
	
	def set_valuation_rate_item(self, item):
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