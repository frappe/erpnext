# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Cast_
from frappe.utils import getdate
from frappe import bold

class ItemPriceDuplicateItem(frappe.ValidationError):
	pass

class COPRate(Document):
	def validate(self):
		self.check_duplicates()

	def check_duplicates(self):
		rate = frappe.db.sql('''
				SELECT rate, name FROM `tabCOP Rate` 
				WHERE item_code = '{item_code}' AND cop_list = '{cop_list}'
				AND name != '{name}' AND valid_from <= ifnull('{valid_from}',NOW())
				AND ifnull(valid_up_to,NOW()) >= '{valid_from}'
			'''.format(item_code = self.item_code, cop_list = self.cop_list, name = self.name, valid_from = self.valid_from), as_dict=True)
		if rate:
			msg = ", ".join(frappe.get_desk_link(self.doctype,d.name) for d in rate)
			frappe.throw(
				_(
					"Fuel Price appears multiple times based on Fuel Price List and Dates.Close following transaction {}".format(msg)
				),
				ItemPriceDuplicateItem,
			)
		cop_rate = frappe.qb.DocType("COP Rate")

		query = (
			frappe.qb.from_(cop_rate)
			.select(cop_rate.rate)
			.where(
				(cop_rate.item_code == self.item_code)
				& (cop_rate.cop_list == self.cop_list)
				& (cop_rate.name != self.name)
			)
		)
		data_fields = (
			"uom",
			"valid_from",
			"valid_up_to",
		)

		for field in data_fields:
			if self.get(field):
				query = query.where(cop_rate[field] == self.get(field))
			else:
				query = query.where(
					Criterion.any(
						[
							cop_rate[field].isnull(),
							Cast_(cop_rate[field], "varchar") == "",
						]
					)
				)

		price_list_rate = query.run(as_dict=True)

		if price_list_rate:
			frappe.throw(
				_(
					"COP Rate appears multiple times based on Cost Of Production List, UOM and Dates."
				),
				ItemPriceDuplicateItem,
			)

@frappe.whitelist()
def get_cop_rate(item_code,posting_date,cop_list,uom=None):
	if not cop_list:
		frappe.throw('COP List is mandatory')
	data = frappe.db.sql('''select rate
					from `tabCOP Rate` where disabled=0 
					and item_code = '{item_code}'
					and valid_from <= '{posting_date}' 
					and (case when valid_up_to then valid_up_to >= '{posting_date}' else '{posting_date}' <= '2099-12-31' end)
					and (case when '{uom}' then uom = '{uom}' else 1 = 1 end)
					and cop_list = '{cop_list}'
					order by valid_from desc
					limit 1
					'''.format(item_code = item_code, posting_date = posting_date, uom=uom, cop_list=cop_list),as_dict=1)
	if not data:
		frappe.msgprint(_("No cop rate found for Item {} under COP List {} for date {}".format(bold(item_code), bold(cop_list), bold(posting_date))), raise_exception=True)
	return data