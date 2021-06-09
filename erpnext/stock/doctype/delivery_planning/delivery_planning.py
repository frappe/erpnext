# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DeliveryPlanning(Document):

	def on_submit(self):
		self.on_delivery_planning_submit()
		self.on_transporter_planning()
		self.on_purchase_planning()


	# @frappe.whitelist()
	# def get_transport(self):
	# 	if self.transporter:
	# 			query = frappe.db.sql(""" Select name
	# 							from `tabSupplier`
	# 							where is_transporter == 1
	# 							"""
	# 			, as_dict=1)
	# 			print ("----------0000000--------",query)
	# 			option_str =''
	# 			for r in query:
	# 				option_str += r.get('name')+"\n"
	# 			return option_str

	# @frappe.whitelist()
	# def get_sales_order(self):
	# 	return self.get_so()
	#
	# @frappe.whitelist()
	# def get_daily_d(self):
	# 	return self.get_dp()
	#
	# @frappe.whitelist()
	# def p_order_create(self):
	# 	return self.p_order()

# # Query for 1st child table Item wise Delivery Planning on button click Item wise Delivery Plan
#
# 	def get_so(self):
# 		conditions = ""
# 		if self.company:
# 			conditions +="AND so.company = %s" % frappe.db.escape(self.company)
#
# 		if self.transporter:
# 			conditions += "AND so.transporter = %s" % frappe.db.escape(self.transporter)
#
# 		if self.delivery_date_from:
# 			conditions += "AND soi.delivery_date >= '%s'" % self.delivery_date_from
#
# 		if self.delivery_date_to:
# 			conditions += "AND soi.delivery_date <= '%s'" % self.delivery_date_to
#
# 		if self.pincode_from:
# 			conditions += "AND so.address_display  LIKE '%s'" % self.pincode_from
#
# 		if self.pincode_to:
# 			conditions += "AND so.address_display  LIKE '%s'" % self.pincode_to
#
# 		query = frappe.db.sql(""" select
# 						so.customer,
# 						soi.item_code,
# 						soi.item_name,
# 						soi.warehouse,
# 						soi.qty,
# 						soi.stock_qty,
# 						so.name,
# 						soi.name as soi_item,
# 						soi.weight_per_unit,
# 						soi.delivery_date,
# 						soi.projected_qty,
# 						so.transporter
#
# 						from `tabSales Order Item` soi
# 						join `tabSales Order` so ON soi.parent = so.name
# 						left outer join `tabAddress` as add on add.name = so.shipping_address_name
#
# 						where so.docstatus = 1
# 						{conditions} """.format(conditions=conditions), as_dict=1)
# 		print(conditions)
# 		return query
#
# # Query for 3rd child table Transporter wise Delivery Planning on button click Get Daily Delivery Plan
#
# 	def get_dp(self):
# 		conditions = ""
# 		if self.company:
# 			conditions += "AND so.company = %s" % frappe.db.escape(self.company)
#
# 		if self.transporter:
# 			conditions += "AND so.transporter = %s" % frappe.db.escape(self.transporter)
#
# 		if self.delivery_date_from:
# 			conditions += "AND so.delivery_date >= '%s'" % self.delivery_date_from
#
# 		if self.delivery_date_to:
# 			conditions += "AND so.delivery_date <= '%s'" % self.delivery_date_to
#
# 		query = frappe.db.sql(""" select
# 					so.transporter,
# 					so.delivery_date,
# 					SUM(so.total_net_weight) AS total_net_weight ,
# 					SUM(so.total_qty) AS total_qty
#
# 					# soi.warehouse,
# 					# soi.weight_per_unit
# 					from `tabSales Order` so
# 					# from `tabSales Order Item` soi
# 					# join `tabSales Order` so ON soi.parent = so.name
#
# 					where so.docstatus = 1
# 					{conditions}
# 					group by so.transporter, so.delivery_date
# 					order by so.delivery_date
# 					""".format(conditions=conditions), as_dict=1)
#
# 						# from `tabSupplier` s
# 						# join `tabSales Order` so ON s.name = so.transporter
# 		return query
# # Query for 3rd child table Order wise Purchase Planning on button click Get Purchase Order To Be Created
# 	def p_order(self):
# 		conditions = ""
# 		if self.company:
# 			conditions += "AND so.company = %s" % frappe.db.escape(self.company)
#
# 		if self.transporter:
# 			conditions += "AND so.transporter = %s" % frappe.db.escape(self.transporter)
#
# 		if self.delivery_date_from:
# 			conditions += "AND so.delivery_date >= '%s'" % self.delivery_date_from
#
# 		if self.delivery_date_to:
# 			conditions += "AND so.delivery_date <= '%s'" % self.delivery_date_to
#
# 		query = frappe.db.sql(""" select
# 					soi.item_code,
# 					soi.item_name,
# 					soi.warehouse,
# 					soi.qty,
# 					so.transporter,
# 					so.name
#
# 					from `tabSales Order Item` soi
# 					join `tabSales Order` so ON soi.parent = so.name
#
# 					where so.docstatus = 1
# 					{conditions} """.format(conditions=conditions), as_dict=1)
# 		return query

	# @frappe.whitelist()
	# def get_options(self):
	# 	query = frappe.db.sql(""" Select pincode
	# 				from `tabAddress`"""
	# 	, as_dict=1)
	# 	print ("------------------",query)
	# 	option_str =''
	# 	for r in query:
	# 		option_str += r.get('pincode')+"\n"
	# 	return option_str
	# Custom button for pick list creation
	# @frappe.whitelist()
	# def make_pick_list(self):
	# 	lst = []
	# 	for itm in self.item_wise_dp:
	# 		lst.append(itm.customer)
	# 	for customer in set(lst):
	# 		doc = frappe.new_doc("Pick List")
	#
	# 		doc.customer = customer
	# 		doc.company = self.company
	# 		doc.purpose = "Delivery"
	# 		doc.parent_warehouse = self.src_warehouse
	# 		for itm in self.item_wise_dp:
	# 			if customer == itm.customer:
	# 				doc.append("locations", {
	# 					"item_name": itm.item_name,
	# 					"item_code": itm.item,
	# 					# "description": itm.description,
	# 					"warehouse": itm.src_warehouse,
	# 					"qty": itm.qty,
	# 					# "uom": itm.uom,
	# 					"stock_qty": itm.c_stock,
	# 					# "stock_uom": itm.stock_uom,
	# 					# "conversion_factor": itm.conversion_factor,
	# 					"sales_order": itm.sales_order,
	# 					# "sales_order_item": itm.sales_order_item,
	# 				})
	# 		doc.set_item_locations()
	# 		doc.insert()
	# 		doc.save()
	def on_delivery_planning_submit(self):
			conditions = ""
			if self.company:
				conditions += "AND so.company = %s" % frappe.db.escape(self.company)

			if self.transporter:
				conditions += "AND so.transporter = %s" % frappe.db.escape(self.transporter)

			if self.delivery_date_from:
				conditions += "AND soi.delivery_date >= '%s'" % self.delivery_date_from

			if self.delivery_date_to:
				conditions += "AND soi.delivery_date <= '%s'" % self.delivery_date_to

			# if self.pincode_from:
			# 	conditions += "And add.pincode >= '%s" % self.pincode_from
			#
			# if self.pincode_to:
			# 	conditions += "And add.pincode <= '%s" % self.pincode_to

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
									so.transporter,
									soi.delivered_by_supplier,
									soi.supplier


									from `tabSales Order Item` soi
									join `tabSales Order` so ON soi.parent = so.name

									where so.docstatus = 1
									{conditions} """.format(conditions=conditions), as_dict=1)
			print("00000000000.0000000000.000000",query)
			for i in query:
				dp_item = frappe.new_doc("Delivery Planning Item")

				dp_item.transporter = i.transporter
				dp_item.customer = i.customer
				dp_item.item_code = i.item_code
				dp_item.item_name = i.item_name

				dp_item.ordered_qty = i.qty
				dp_item.pending_qty = i.qty
				dp_item.qty_to_deliver = i.qty
				dp_item.weight_to_deliver = i.weight_per_unit * i.qty
				dp_item.sales_order = i.name
				dp_item.source_warehouse = i.warehouse
				dp_item.postal_code = 0
				dp_item.delivery_date = i.delivery_date
				dp_item.current_stock = i.projected_qty - i.stock_qty
				dp_item.available_stock = i.projected_qty
				dp_item.related_delivey_planning = self.name
				dp_item.weight_per_unit = i.weight_per_unit
				dp_item.supplier_dc = i.delivered_by_supplier
				dp_item.supplier = i.supplier

				dp_item.save(ignore_permissions = True)

	def on_transporter_planning(self):
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

							from `tabSales Order` so
							# from `tabSales Order Item` soi
							# join `tabSales Order` so ON soi.parent = so.name

							where so.docstatus = 1
							{conditions}
							group by so.transporter, so.delivery_date

							""".format(conditions=conditions), as_dict=1)

							# from `tabSupplier` s
							# join `tabSales Order` so ON s.name = so.transporter

		for i in query:
			dp_item = frappe.new_doc("Transporter Wise Planning Item")
			dp_item.transporter = i.transporter
			dp_item.delivery_date = i.delivery_date
			dp_item.weight_to_deliver = i.total_net_weight
			dp_item.quantity_to_deliver = i.total_qty
			dp_item.source_warehouse = ""
			dp_item.related_delivery_planning = self.name
			dp_item.save(ignore_permissions=True)


	def on_purchase_planning(self):
		conditions = ""
		if self.company:
			conditions += "AND so.company = %s" % frappe.db.escape(self.company)

		if self.transporter:
			conditions += "AND so.transporter = %s" % frappe.db.escape(self.transporter)

		if self.delivery_date_from:
			conditions += "AND soi.delivery_date >= '%s'" % self.delivery_date_from

		if self.delivery_date_to:
			conditions += "AND soi.delivery_date <= '%s'" % self.delivery_date_to

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

		for i in query:
			dp_item = frappe.new_doc("Purchase Orders Planning Item")
			dp_item.sales_order = i.sales_order
			dp_item.item_code = i.item_code
			dp_item.item_name = i.item_name
			dp_item.supplier = i.transporter
			dp_item.related_delivery_planning = self.name
			dp_item.save(ignore_permissions=True)

# left outer join `tabAddress` as add on add.address_title = so.customer
