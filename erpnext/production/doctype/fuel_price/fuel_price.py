# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Cast_
from frappe.utils import getdate

class ItemPriceDuplicateItem(frappe.ValidationError):
	pass

class FuelPrice(Document):
	def validate(self):
		self.check_duplicates()
		if self.valid_up_to and self.valid_from > self.valid_up_to:
			frappe.throw("Valid From cannot be greater than Valid Up To")
	def check_duplicates(self):
	# select rate from `tabFuel Price` where item_code = '' and name != self.name and valid_from <= ifnull(self.valid_up_to,now) and ifnull(valid_up_to,now) >= self.valid_from
		rate = frappe.db.sql('''
				SELECT rate, name FROM `tabFuel Price` 
				WHERE item_code = '{item_code}' AND fuel_price_list = '{fuel_price_list}'
				AND name != '{name}' AND valid_from <= ifnull('{valid_from}',NOW())
				AND ifnull(valid_up_to,NOW()) >= '{valid_from}'
			'''.format(item_code = self.item_code, fuel_price_list = self.fuel_price_list, name = self.name, valid_from = self.valid_from), as_dict=1)
		if rate:
			msg = ", ".join(frappe.get_desk_link(self.doctype,d.name) for d in rate)
			frappe.throw(
				_(
					"Fuel Price appears multiple times based on Fuel Price List and Dates.Close following transaction {}".format(frappe.bold(msg))
				),
				ItemPriceDuplicateItem,
			)
		fuel_price = frappe.qb.DocType("Fuel Price")
		query = (
			frappe.qb.from_(fuel_price)
			.select(fuel_price.rate)
			.where(
				(fuel_price.item_code == self.item_code)
				& (fuel_price.fuel_price_list == self.fuel_price_list)
				& (fuel_price.name != self.name)
			)
		)
		data_fields = (
			"uom",
			"valid_from",
			"valid_up_to",
		)

		for field in data_fields:
			if self.get(field):
				query = query.where(fuel_price[field] == self.get(field))
			else:
				query = query.where(
					Criterion.any(
						[
							fuel_price[field].isnull(),
							Cast_(fuel_price[field], "varchar") == "",
						]
					)
				)

		price_list_rate = query.run(as_dict=True)

		if price_list_rate:
			frappe.throw(
				_(
					"Fuel Price appears multiple times based on Fuel Price List, UOM and Dates."
				),
				ItemPriceDuplicateItem,
			)
			
@frappe.whitelist()
def get_previous_price(item_code, valid_from, fuel_price_list, uom=None):
	if not item_code or not valid_from or not fuel_price_list:
		frappe.throw('Either one of these (Item, Valid From, Fuel Price List) are not provide ')
	return frappe.db.sql('''select rate
					from `tabFuel Price` where disabled=0 
					and item_code = '{item_code}'
					and valid_up_to < '{valid_from}'
					and disabled = 0 
					and (case when '{uom}' then uom = '{uom}' else 1 = 1 end)
					and fuel_price_list = '{fuel_price_list}'
					order by valid_up_to desc
					limit 1
					'''.format(item_code = item_code, valid_from = valid_from, uom=uom, fuel_price_list=fuel_price_list),as_dict=1)

@frappe.whitelist()
def get_current_fuel_price(item_code,valid_from,fuel_price_list,uom=None):
	if not fuel_price_list:
		frappe.throw('Fuel Price List is mandatory')
	return frappe.db.sql('''select rate
					from `tabFuel Price` where disabled=0 
					and item_code = '{item_code}'
					and disabled = 0
					and valid_from <= '{valid_from}' 
					and (case when valid_up_to then valid_up_to >= '{valid_from}' else '{valid_from}' <= '2099-12-31' end)
					and (case when '{uom}' then uom = '{uom}' else 1 = 1 end)
					and fuel_price_list = '{fuel_price_list}'
					order by valid_from desc
					limit 1
					'''.format(item_code = item_code, valid_from = valid_from, uom=uom, fuel_price_list=fuel_price_list),as_dict=1)

