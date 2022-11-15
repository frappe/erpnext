# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, getdate


class LCCostingReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

	def run(self):
		self.get_data()
		self.get_price_list_details()
		self.process_data()
		columns = self.get_columns()

		return columns, self.data

	def get_data(self):
		conditions = self.get_conditions()

		self.data = frappe.db.sql("""
			select lc.name, lc.posting_date, lc.currency, lc.company,
				lc_item.item_code, lc_item.item_name,
				lc_item.qty, lc_item.uom, lc_item.weight,
				lc_item.rate, lc_item.amount, lc_item.applicable_charges,
				(lc_item.amount + lc_item.applicable_charges) as landed_cost,
				(lc_item.amount + lc_item.applicable_charges) / lc_item.qty as landed_rate
			from `tabLanded Cost Item` lc_item
			inner join `tabLanded Cost Voucher` lc on lc.name = lc_item.parent
			where lc.docstatus < 2 {0}
		""".format(conditions), self.filters, as_dict=1)

		return self.data

	def get_price_list_details(self):
		self.filters.price_list_currency = None
		if self.filters.reference_price_list:
			self.filters.price_list_currency = frappe.db.get_value("Price List", self.filters.reference_price_list, 'currency')

	def process_data(self):
		for d in self.data:
			d["disable_item_formatter"] = cint(self.show_item_name)

			if self.filters.reference_price_list:
				d.reference_rate = self.get_item_price(d)
				d.reference_rate_currency = self.filters.price_list_currency

	def get_item_price(self, d):
		from erpnext.stock.get_item_details import get_item_price

		item_price_args = {
			"item_code": d.item_code,
			"price_list": self.filters.reference_price_list,
			"uom": d.uom,
			"transaction_date": getdate(d.posting_date),
		}
		current_rate = get_item_price(item_price_args, d.item_code)
		current_rate = current_rate[0][1] if current_rate else None
		return current_rate

	def get_conditions(self):
		conditions = []

		if self.filters.landed_cost_voucher:
			conditions.append("lc.name = %(landed_cost_voucher)s")

		if self.filters.from_date:
			conditions.append("lc.posting_date >= %(from_date)s")

		if self.filters.to_date:
			conditions.append("lc.posting_date <= %(to_date)s")

		if self.filters.item_code:
			conditions.append("lc_item.item_code = %(item_code)s")

		return "and {0}".format(" and ".join(conditions)) if conditions else ""

	def get_columns(self):
		columns = [
			{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 80},
			{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item",
				"width": 100 if self.show_item_name else 150},
		]

		if self.show_item_name:
			columns.append({"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150})

		columns += [
			{"label": _("Qty"), "fieldtype": "Float", "fieldname": "qty", "width": 80},
			{"label": _("UOM"), "fieldtype": "Link", "options": "UOM", "fieldname": "uom", "width": 50},
			{"label": _("Weight"), "fieldtype": "Float", "fieldname": "weight", "width": 80},
			{"label": _("Rate"), "fieldtype": "Currency", "fieldname": "rate", "width": 120,
				"options": "Company:company:default_currency"},
			{"label": _("Amount"), "fieldtype": "Currency", "fieldname": "amount", "width": 120,
				"options": "Company:company:default_currency"},
			{"label": _("Charges"), "fieldtype": "Currency", "fieldname": "applicable_charges", "width": 120,
				"options": "Company:company:default_currency"},
			{"label": _("Landed Cost"), "fieldtype": "Currency", "fieldname": "landed_cost", "width": 120,
				"options": "Company:company:default_currency"},
			{"label": _("Landed Rate"), "fieldtype": "Currency", "fieldname": "landed_rate", "width": 120,
				"options": "Company:company:default_currency"},
		]

		if self.filters.reference_price_list:
			columns.append({
				"label": _("{0} Rate").format(self.filters.reference_price_list),
				"fieldname": "reference_rate",
				"fieldtype": "Currency",
				"options": "reference_rate_currency",
				"price_list": self.filters.reference_price_list,
				"editable": 1,
			})

		return columns


def execute(filters=None):
	return LCCostingReport(filters).run()
