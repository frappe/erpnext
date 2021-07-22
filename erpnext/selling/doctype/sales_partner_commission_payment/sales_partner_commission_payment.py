# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SalesPartnerCommissionPayment(Document):
	def get_entries(self):
		date_field = ("transaction_date" if self.based_on == "Sales Order"
			else "posting_date")
		conditions = "1=1"
		# for field in ["company", "customer", "territory", "sales_partner"]:
		# 	if self.field:
		# 		conditions += " and dt.{0} = %({1})s".format(field, self.field)
		# print(conditions)
		if self.company:
			print("company")
			conditions += " and dt.company = '{}'".format(self.company)
			
		if self.customer:
			print("customer")
			conditions += " and dt.customer = '{}'".format(self.customer)
			
		if self.territory:
			print("territory")
			conditions += " and dt.territory = '{}'".format(self.territory)

		if self.sales_partner:
			print("sales_partner")
			conditions += " and dt.sales_partner = '{}'".format(self.sales_partner)
	
		if self.from_date:
			conditions += " and dt.{0} >= '{1}'".format(date_field, self.from_date)

		if self.to_date:
			conditions += " and dt.{0} <= '{1}'".format(date_field, self.to_date)

		if not self.show_return_entries:
			conditions += " and dt_item.qty > 0.0"

		if self.brand:
			conditions += " and dt_item.brand = '{}".format(self.brand)

		if self.item_group:
			lft, rgt = frappe.get_cached_value('Item Group',
				self.item_group, ['lft', 'rgt'])

			conditions += """ and dt_item.item_group in (select name from
				`tabItem Group` where lft >= %s and rgt <= %s)""" % (lft, rgt)

		query = """
			SELECT
				dt.name, dt.customer, dt.territory, dt.{date_field} as posting_date, dt.currency,
				dt_item.base_net_rate as rate, dt_item.qty, dt_item.base_net_amount as amount,
				((dt_item.base_net_amount * dt.commission_rate) / 100) as commission,
				dt_item.brand, dt.sales_partner, dt.commission_rate, dt_item.item_group, dt_item.item_code
			FROM
				`tab{doctype}` dt, `tab{doctype} Item` dt_item
			WHERE
				{cond} and dt.name = dt_item.parent and dt.docstatus = 1
				and dt.sales_partner is not null and dt.sales_partner != ''
				order by dt.name desc, dt.sales_partner
			""".format(date_field=date_field, doctype=self.based_on,
				cond=conditions)
		print(query)
		entries = frappe.db.sql(query, as_dict = True)
		return entries
	
	def get_sales_invoice_data(self):
		query1 = """
					SELECT customer, item_code, commission 

					FROM `tab{doctype} Table`

					WHERE docstatus = 1 and posting_date >= %s and posting_date <= %s order by customer asc
				""".format(doctype = self.based_on)
		entries1 = frappe.db.sql(query1,(self.from_date, self.to_date), as_dict = True)

		if(entries1):
			present_name = entries1[0].customer
			spcp = frappe.new_doc("Sales Invoice")
			spcp.customer = present_name
			spcp.is_return = 1
			spcp.date = frappe.utils.today()
			spcp.due_date = frappe.utils.today()
			spcp.selling_price_list = "Standard Selling"
			for value in entries1:
				if(value['customer'] == present_name):
					spcp.append('items', {
					'item_code': value['item_code'],
					'qty': -1,
					'rate': value['commission']
					})
				else:
					spcp.save(ignore_permissions=True)
					present_name = value['customer']
					spcp = frappe.new_doc("Sales Invoice")
					spcp.customer = value['customer']
					spcp.is_return = 1
					spcp.date = frappe.utils.today()
					spcp.due_date = frappe.utils.today()
					spcp.selling_price_list = "Standard Selling"
					spcp.append('items', {
					'item_code': value['item_code'],
					'qty': -1,
					'rate': value['commission']
					})
			spcp.save(ignore_permissions=True)
			return True
		