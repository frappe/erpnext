# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime

class InventoryDownload(Document):
	def validate(self):
		if self.docstatus == 1:
			self.apply_inventory_download()
			self.set_valuation_rate()

			for item in self.get("items"):
				items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})

				for bin in items_bin:
					if self.warehouse == bin.warehouse:
						doc = frappe.get_doc("Bin", bin.name)
						self.create_stock_ledger_entry(item, doc.actual_qty, 0)
	
	def on_cancel(self):
		self.delete_bin()
		self.apply_inventory_download_cancel()
		self.delete_stock_ledger_entry()
	
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
			frappe.delete_doc("Stock Ledger Entry", stock.name)
	
	def set_valuation_rate(self):
		
		for item in self.get("items"):
			stock = frappe.get_all("Stock Ledger Entry", ["*"], filters = {"item_code": item.item_code})

			stock_reversed = list(reversed(stock))

			doc = frappe.get_doc("Inventory Download Detail", item.name)
			doc.db_set('valuation_rate', stock[0].valuation_rate, update_modified=False)
	
	def delete_bin(self):
		for item in self.get("items"):
			items_bin = frappe.get_all("Bin", ["*"], filters = {"item_code": item.item_code})

			for bin in items_bin:
				if self.warehouse == bin.warehouse:
					doc = frappe.get_doc("Bin", bin.name)
					doc.actual_qty -= item.qty
					doc.db_set('actual_qty', doc.actual_qty, update_modified=False)
					self.create_stock_ledger_entry(item, doc.actual_qty, 1)
	
	def create_stock_ledger_entry(self, item, qty, delete):
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
		now = datetime.now()
		doc = frappe.new_doc("Stock Ledger Entry")
		doc.item_code = item.item_code
		doc.batch_no = item.batch_no
		doc.warehouse = self.warehouse
		doc.serial_no = item.serial_no
		doc.posting_date = now.date()
		doc.posting_time = now.time()
		doc.voucher_type =  self.doctype
		doc.voucher_no = self.name
		doc.voucher_detail_no = self.name
		doc.actual_qty = qty_item
		doc.incoming_rate = 0
		doc.outgoing_rate = 0
		doc.stock_uom = item.stock_uom
		doc.qty_after_transaction = qty
		doc.valuation_rate = item.basic_rate
		doc.stock_value = qty * item.basic_rate
		doc.stock_value_difference = qty_item * item.basic_rate
		doc.company = self.company
		doc.fiscal_year = fiscal_year[0].name
		doc.insert()