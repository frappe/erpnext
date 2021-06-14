# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DeliveryPlanning(Document):

	def on_submit(self):
		self.on_delivery_planning_submit()
		print("Calling DPI")
		# self.on_transporter_planning()
		# self.on_purchase_planning()


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

	# on click of custom button Calculate Purchase Order Plan Summary create new PODPI
	@frappe.whitelist()
	def purchase_order_call(self):
		conditions = ""
		item = frappe.get_all(doctype='Delivery Planning Item',
							  	  filters={"approved": "Yes",
										   "supplier_dc": 1,
								  "related_delivey_planning" : self.name})
		print("<<<<<<<<<< Po plan >>>>>>>>>>>>>>>>>",item)

		if(item):

			for i in item:

				popi = frappe.db.get_all(doctype= 'Purchase Orders Planning Item',
								filters={"related_delivery_planning" : self.name})


				if popi:
					for p in popi:
						frappe.db.delete('Purchase Orders Planning Item', {
										'name': p.name
						})
						print("-----------Deleted TDPi Id--------------",p.name)

					conditions += "AND related_delivey_planning = %s" % frappe.db.escape(self.name)
					query = frappe.db.sql(""" select
									sales_order,
									item_code,
									item_name,
									ordered_qty,
									supplier,
									name

									from `tabDelivery Planning Item`

									where supplier_dc = 1
									{conditions} """.format(conditions=conditions), as_dict=1)

					for q in query:
						dp_item = frappe.new_doc("Purchase Orders Planning Item")
						dp_item.sales_order = q.sales_order
						dp_item.item_code = q.item_code
						dp_item.item_name = q.item_name
						dp_item.supplier = q.supplier
						dp_item.qty_to_order = q.ordered_qty
						dp_item.related_delivery_planning = self.name
						dp_item.rdp_item = q.name
						dp_item.save(ignore_permissions=True)

				else:
						conditions += "AND related_delivey_planning = %s" % frappe.db.escape(self.name)
						query = frappe.db.sql(""" select
											sales_order,
											item_code,
											item_name,
											ordered_qty,
											supplier,
											name

											from `tabDelivery Planning Item`

											where supplier_dc = 1
											{conditions} """.format(conditions=conditions), as_dict=1)

						for q in query:
							p_item = frappe.new_doc("Purchase Orders Planning Item")
							p_item.sales_order = q.sales_order
							p_item.item_code = q.item_code
							p_item.item_name = q.item_name
							p_item.supplier = q.supplier
							p_item.qty_to_order = q.ordered_qty
							p_item.related_delivery_planning = self.name
							p_item.rdp_item = q.name
							p_item.save(ignore_permissions=True)

			return 1
		return 0

# Creating Transporter wise delivery planning item
	@frappe.whitelist()
	def summary_call(self):
		conditions = ""
		print("----------0000000000 this is  Transporter wise delivery call ------------")
		item = frappe.db.get_all(doctype='Delivery Planning Item',
								  filters={"approved": "Yes",
										   "related_delivey_planning": self.name})
		print("<<<<<<<<<<>>  Transporter wise delivery >>>>>>>>>>>>>>>", item)

		if (item):
			print("-----------D gfhgfhfg --------------",item)
			for i in item:
				popi = frappe.db.get_all(doctype='Transporter Wise Planning Item',
										  filters={"related_delivery_planning": self.name})

				if popi:
					for p in popi:
						frappe.db.delete('Transporter Wise Planning Item', {
							'name': p.name
						})
						print("-----------Deleted TDPi Id--------------", p.name)

					conditions += "AND related_delivey_planning = %s" % frappe.db.escape(self.name)
					query = frappe.db.sql(""" select
											transporter,
											delivery_date,
											sum(weight_to_deliver) as total_weight,
											sorce_warehouse,
											sum(ordered_qty) as total_qty,
											name

											from `tabDelivery Planning Item`

											where approved = "Yes"
											{conditions}
											group by transporter, delivery_date
											""".format(conditions=conditions), as_dict=1)

					for q in query:
						dp_item = frappe.new_doc("Transporter Wise Planning Item")
						dp_item.transporter = q.transporter
						dp_item.delivery_date = q.delivery_date
						dp_item.weight_to_deliver = q.total_weight
						dp_item.quantity_to_deliver = q.total_qty
						dp_item.source_warehouse = q.sorce_warehouse
						dp_item.related_delivery_planning = self.name

						# code for test
						so_wise_data = frappe.db.get_all("Delivery Planning Item",
								{"related_delivey_planning" :self.name, "transporter" : q.transporter },
								["sales_order","item_name","ordered_qty","weight_to_deliver"]
						)
						print("0000000000000000000000000000",so_wise_data)
						if(so_wise_data):
							for s in so_wise_data:
								dp_item.append("items",{"sales_order": s.sales_order,
														 "item_name": s.item_name,
														 "qty": s.ordered_qty,
										   				 "weight": s.weight_to_deliver
														 })
						dp_item.save(ignore_permissions=True)

						print("aaaaaaa0000000 ..........",q.total_weight)

				else:
					conditions += "AND related_delivey_planning = %s" % frappe.db.escape(self.name)
					query = frappe.db.sql(""" select
										transporter,
										delivery_date,
										sum(weight_to_deliver) as total_weight,
										sorce_warehouse,
										sum(ordered_qty) as total_qty,
										name

										from `tabDelivery Planning Item`

										where approved = "Yes"
										{conditions}
										group by transporter, delivery_date
										""".format(conditions=conditions), as_dict=1)

					for q in query:
						dp_item = frappe.new_doc("Transporter Wise Planning Item")
						dp_item.transporter = q.transporter
						dp_item.delivery_date = q.delivery_date
						dp_item.weight_to_deliver = q.total_weight
						dp_item.quantity_to_deliver = q.total_qty
						dp_item.source_warehouse = q.sorce_warehouse

						so_wise_data = frappe.db.get_all("Delivery Planning Item",
														 {"related_delivey_planning": self.name,
														  "transporter": q.transporter},
														 ["sales_order", "item_name", "ordered_qty",
														  "weight_to_deliver"]
														 )
						print("0000000000000000000000000000", so_wise_data)
						if (so_wise_data):
							for s in so_wise_data:
								dp_item.append("items", {"sales_order": s.sales_order,
														 "item_name": s.item_name,
														 "qty": s.ordered_qty,
														 "weight": s.weight_to_deliver
														 })

						dp_item.related_delivery_planning = self.name


						dp_item.save(ignore_permissions=True)
						print("-----------Date 0000000 TDPi Id--------------",q.delivery_date)
			return 1
		else:
			return 0


