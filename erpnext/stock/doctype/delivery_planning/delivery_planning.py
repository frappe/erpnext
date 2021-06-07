# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DeliveryPlanning(Document):
	@frappe.whitelist()
	def get_pin(self):
		if self.pincode_from:
			pin = frappe.get_list('Address', fields = ['pincode'])
			print("111111111110000000555550000000011111111111",pin)
			return pin

	@frappe.whitelist()
	def get_sales_order(self):
		return self.get_so()

	@frappe.whitelist()
	def get_daily_d(self):
		return self.get_dp()

	@frappe.whitelist()
	def p_order_create(self):
		return self.p_order()

# Query for 3rd child table Item wise Delivery Planning on button click Item wise Delivery Plan

	def get_so(self):
		conditions = ""
		if self.company:
			conditions +="AND so.company = %s" % frappe.db.escape(self.company)

		if self.transporter:
			conditions += "AND so.transporter = %s" % frappe.db.escape(self.transporter)

		if self.delivery_date_from:
			conditions += "AND soi.delivery_date >= '%s'" % self.delivery_date_from

		if self.delivery_date_to:
			conditions += "AND soi.delivery_date <= '%s'" % self.delivery_date_to

		if self.pincode_from:
			conditions += "AND so.address_display  LIKE '%s'" % self.pincode_from

		if self.pincode_to:
			conditions += "AND so.address_display  LIKE '%s'" % self.pincode_to

		query = frappe.db.sql(""" select
						so.customer,
						soi.item_code,
						soi.item_name,
						soi.warehouse,
						soi.qty,
						soi.stock_qty,
						so.name,
						soi.name as soi_item,
						soi.weight_per_unit,
						soi.delivery_date,
						soi.projected_qty,
						so.transporter

						from `tabSales Order Item` soi
						join `tabSales Order` so ON soi.parent = so.name

						where so.docstatus = 1
						{conditions} """.format(conditions=conditions), as_dict=1)
		print(conditions)
		return query

# Query for 3rd child table Transporter wise Delivery Planning on button click Get Daily Delivery Plan

	def get_dp(self):
		conditions = ""
		if self.company:
			conditions += "AND so.company = %s" % frappe.db.escape(self.company)

		if self.transporter:
			conditions += "AND so.transporter = %s" % frappe.db.escape(self.transporter)

		if self.delivery_date_from:
			conditions += "AND so.delivery_date >= '%s'" % self.delivery_date_from

		if self.delivery_date_to:
			conditions += "AND so.delivery_date <= '%s'" % self.delivery_date_to

		query = frappe.db.sql(""" select
					so.transporter,
					so.delivery_date,
					SUM(so.total_net_weight) AS total_net_weight ,
					SUM(so.total_qty) AS total_qty

					# soi.warehouse,
					# soi.weight_per_unit
					from `tabSales Order` so
					# from `tabSales Order Item` soi
					# join `tabSales Order` so ON soi.parent = so.name

					where so.docstatus = 1
					{conditions}
					group by so.transporter, so.delivery_date
					order by so.delivery_date
					""".format(conditions=conditions), as_dict=1)

						# from `tabSupplier` s
						# join `tabSales Order` so ON s.name = so.transporter
		return query
# Query for 3rd child table Order wise Purchase Planning on button click Get Purchase Order To Be Created
	def p_order(self):
		conditions = ""
		if self.company:
			conditions += "AND so.company = %s" % frappe.db.escape(self.company)

		if self.transporter:
			conditions += "AND so.transporter = %s" % frappe.db.escape(self.transporter)

		if self.delivery_date_from:
			conditions += "AND so.delivery_date >= '%s'" % self.delivery_date_from

		if self.delivery_date_to:
			conditions += "AND so.delivery_date <= '%s'" % self.delivery_date_to

		query = frappe.db.sql(""" select
					soi.item_code,
					soi.item_name,
					soi.warehouse,
					soi.qty,
					so.transporter,
					so.name

					from `tabSales Order Item` soi
					join `tabSales Order` so ON soi.parent = so.name

					where so.docstatus = 1
					{conditions} """.format(conditions=conditions), as_dict=1)
		return query

	@frappe.whitelist()
	def get_options(self):
		query = frappe.db.sql(""" Select pincode
					from `tabAddress`"""
		, as_dict=1)
		print ("------------------",query)
		option_str =''
		for r in query:
			option_str += r.get('pincode')+"\n"
		return option_str
