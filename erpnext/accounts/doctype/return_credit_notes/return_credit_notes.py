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
from datetime import datetime

class Returncreditnotes(Document):
	def before_insert(self):
		if self.docstatus == 0:
			self.assign_cai()

	def validate(self):		
		if self.docstatus == 0:
			if self.grand_total > 0:
				items = frappe.get_all("Return credit notes Item", ["*"], filters = {"parent": self.name})
				self.delete_items(items)

			self.get_items()
	
	def delete_items(self, items):
		for item in items:
			frappe.delete_doc("Return credit notes Item", item.name)

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
	
	def assign_cai(self):
		user = frappe.session.user

		# user_name = frappe.get_all("User", ["first_name"], filters = {"email": user})

		cai = frappe.get_all("CAI", ["initial_number", "final_number", "name_cai", "cai", "issue_deadline", "prefix"], filters = { "status": "Active", "prefix": self.naming_series})

		if len(cai) == 0:
			frappe.throw(_("This secuence no assign cai"))

		current_value = self.get_current(cai[0].prefix)

		now = datetime.now()

		date = now.date()

		number_final = current_value + 1

		if number_final <= int(cai[0].final_number) and str(date) <= str(cai[0].issue_deadline):
			self.assing_data(cai[0].cai, cai[0].issue_deadline, cai[0].initial_number, cai[0].final_number, user, cai[0].prefix)

			amount = int(cai[0].final_number) - current_value

			self.alerts(cai[0].issue_deadline, amount)
		else:
			cai_secondary = frappe.get_all("CAI", ["initial_number", "final_number", "name_cai", "cai", "issue_deadline", "prefix"], filters = { "status": "Pending", "prefix": self.naming_series})
			
			if len(cai_secondary) > 0:
				final = int(cai[0].final_number) + 1
				initial = int(cai_secondary[0].initial_number)
				if final == initial:
					self.assing_data(cai_secondary[0].cai, cai_secondary[0].issue_deadline, cai_secondary[0].initial_number, cai_secondary[0].final_number, user, cai_secondary[0].prefix)
					doc = frappe.get_doc("CAI", cai[0].name_cai)
					doc.status = "Inactive"
					doc.save()

					doc_sec = frappe.get_doc("CAI", cai_secondary[0].name_cai)
					doc_sec.status = "Active"
					doc_sec.save()

					new_current = int(cai_secondary[0].initial_number) - 1
					name = self.parse_naming_series(cai_secondary[0].prefix)

					frappe.db.set_value("Series", name, "current", new_current, update_modified=False)
				else:
					self.assing_data(cai[0].cai, cai[0].issue_deadline, cai[0].initial_number, cai[0].final_number, user, cai[0].prefix)
					frappe.throw("The CAI you are using is expired.")
			else:
				self.assing_data(cai[0].cai, cai[0].issue_deadline, cai[0].initial_number, cai[0].final_number, user, cai[0].prefix)
				frappe.throw("The CAI you are using is expired.")
	
	def get_current(self, prefix):
		pre = self.parse_naming_series(prefix)
		current_value = frappe.db.get_value("Series",
		pre, "current", order_by = "name")
		return current_value

	def parse_naming_series(self, prefix):
		parts = prefix.split('.')
		if parts[-1] == "#" * len(parts[-1]):
			del parts[-1]

		pre = parse_naming_series(parts)
		return pre
	
	def assing_data(self, cai, issue_deadline, initial_number, final_number, user, prefix):
		pre = self.parse_naming_series(prefix)

		self.cai = cai

		self.due_date_cai = issue_deadline

		self.authorized_range = "{}{} al {}{}".format(pre, self.serie_number(int(initial_number)), pre, self.serie_number(int(final_number)))

		self.cashier = user
	
	def serie_number(self, number):

		if number >= 1 and number < 10:
			return("0000000" + str(number))
		elif number >= 10 and number < 100:
			return("000000" + str(number))
		elif number >= 100 and number < 1000:
			return("00000" + str(number))
		elif number >= 1000 and number < 10000:
			return("0000" + str(number))
		elif number >= 10000 and number < 100000:
			return("000" + str(number))
		elif number >= 100000 and number < 1000000:
			return("00" + str(number))
		elif number >= 1000000 and number < 10000000:
			return("0" + str(number))
		elif number >= 10000000:
			return(str(number))
	
	def alerts(self, date, amount):
		gcai_setting = frappe.get_all("Cai Settings", ["expired_days", "expired_amount"])

		if len(gcai_setting) > 0:
			if amount <= gcai_setting[0].expired_amount:
				amount_rest = amount - 1
				frappe.msgprint(_("There are only {} numbers available for this CAI.".format(amount_rest)))
		
			now = date.today()
			days = timedelta(days=int(gcai_setting[0].expired_days))

			sum_dates = now+days

			if str(date) <= str(sum_dates):
				for i in range(int(gcai_setting[0].expired_days)):		
					now1 = date.today()
					days1 = timedelta(days=i)

					sum_dates1 = now1+days1
					if str(date) == str(sum_dates1):
						frappe.msgprint(_("This CAI expires in {} days.".format(i)))
						break