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
									soi.supplier,
									soi.uom,
									soi.conversion_factor,
									soi.stock_uom


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
			dp_item.sorce_warehouse = i.warehouse
			dp_item.postal_code = 0
			dp_item.delivery_date = i.delivery_date
			dp_item.current_stock = i.projected_qty - i.stock_qty
			dp_item.available_stock = i.projected_qty
			dp_item.related_delivey_planning = self.name
			dp_item.weight_per_unit = i.weight_per_unit
			dp_item.supplier_dc = i.delivered_by_supplier
			dp_item.supplier = i.supplier
			dp_item.uom = i.uom
			dp_item.conversion_factor = i.conversion_factor
			dp_item.stock_uom = i.stock_uom
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

					conditions = ""
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
					conditions = ""
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

		print("----------0000000000 this is  Transporter wise delivery call ------------")
		item = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={"approved": "Yes",
										  "supplier_dc": 0,
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
					conditions = ""
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
											AND supplier_dc = 0
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
														 {"related_delivey_planning" :self.name,
														  "transporter" : q.transporter,
														  "delivery_date" : q.delivery_date,
														  "approved": "Yes",
														  "supplier_dc" : 0},
														 ["sales_order","item_name",
														  "ordered_qty","weight_to_deliver"]
														 )
						print("000000000000000 1 if 0000000000000",so_wise_data)
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
					conditions = ""
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
														  "transporter": q.transporter,
														  "approved": "Yes",
														  },
														 ["sales_order", "item_name", "ordered_qty",
														  "weight_to_deliver"]
														 )
						print("000000000000 2 if 0000000000000000", so_wise_data)
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

	@frappe.whitelist()
	def make_po(self):
		salesno = 0
		discount = []
		print("------------- inside PO make po ---------")
		item = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={"approved": "Yes",
										  "supplier_dc": 1,
										  "related_delivey_planning": self.name})
		print("<<<<<<<<<<>>  Create PO after item >>>>>>>>>>>>>>>", item)
		if (item):
			print("-----------D gfhgfhfg --------------", item)
			for i in item:
				conditions = ""
				conditions += "AND dpi.related_delivey_planning = %s" % frappe.db.escape(self.name)
				print("Condition000000000000000000 ",conditions)
				query = frappe.db.sql(""" select
										dpi.supplier,
										sum(dpi.ordered_qty) t_qty,
										sum(dpi.weight_to_deliver) t_weight

										from `tabDelivery Planning Item`dpi

										where dpi.supplier_dc = 1
										AND dpi.approved = "Yes"

										{conditions}
										group by dpi.supplier
										""".format(conditions=conditions), as_dict=1)

			for q in query:
				po = frappe.new_doc("Purchase Order")
				po.supplier = q.supplier
				po.total_qty = q.t_qty
				po.total_net_weight = q.t_weight
				po.related_delivery_planning = self.name

				so_wise_data = frappe.db.get_all("Delivery Planning Item",
												 {"related_delivey_planning": self.name,
												  "supplier": q.supplier,
												  "approved": "Yes"},
												 ["item_code",
												  "item_name",
												  "ordered_qty",
												  "delivery_date",
												  "sorce_warehouse",
												  "sales_order",
												  "name"
												 ]
												 )
				print("0000000000000000000000000000", so_wise_data)
				if (so_wise_data):
					for s in so_wise_data:
						salesno = s.sales_order
						po.append("items", {"item_code": s.item_code,
											 "item_name": s.item_name,
											 "schedule_date":s.delivery_date,
											 "qty": s.ordered_qty,
											 "warehouse": s.sorce_warehouse
											 })

				discount = frappe.get_doc('Sales Order', salesno)
				print("po........p.o........po", discount.additional_discount_percentage)

				# tax = frappe.get_list('Sales Taxes and Charges',
				# 					  filters={'parent': salesno},
				# 					  fields=["charge_type",
				# 							  "account_head",
				# 							  "description",
				# 							  "rate"]
				# 					  )
				# print("--------- this  is taxes--------", tax)
				# for t in tax:
				# 	dnote.append('taxes', {
				# 		'charge_type': t.charge_type,
				# 		'description': t.description,
				# 		'account_head': t.account_head,
				# 		'rate': t.rate
				# 	})

				# po.additional_discount_percentage = discount.additional_discount_percentage
				# po.apply_dicount_on = discount.apply_discount_on
				# po.taxes_and_charges = discount.taxes_and_charges

				po.save(ignore_permissions=True)
				# po.save()
				# frappe.db.commit()
				print("-----------Date 0purchase order create 111 -------------", q.delivery_date)
				for i in so_wise_data:
						newdoc = frappe.get_doc('Delivery Planning Item', i.name)
						newdoc.purchase_order = po.name 
						newdoc.d_status = "Complete"
						newdoc.save(ignore_permissions=True)

			return 1

	@frappe.whitelist()
	def make_picklist(self):
		print("------------- inside PI make picklist ---------")

		item = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={"approved": "Yes",
										  "supplier_dc": 0,
										  "related_delivey_planning": self.name,
										  })
		print("<<<<<<<<<<>>  Create pi after item >>>>>>>>>>>>>>>", item)
		if (item):
			print("-----------D gfhgfhfg --------------", item)
			for i in item:
				conditions = ""
				conditions += "AND dpi.related_delivey_planning = %s" % frappe.db.escape(self.name)
				print("Condition000000000000000000 ", conditions)
				query = frappe.db.sql(""" select
										transporter,
										customer,
										sum(dpi.weight_to_deliver) t_weight

										from `tabDelivery Planning Item`dpi

										where dpi.supplier_dc = 0
										AND dpi.approved = "Yes"
										AND dpi.transporter IS NOT NULL
										{conditions}
										group by dpi.transporter, dpi.customer
										""".format(conditions=conditions), as_dict=1)
			for q in query:
				print(" query -------", q)
				pi = frappe.new_doc("Pick List")
				pi.customer = q.customer
				pi.purpose = "Delivery"
				pi.related_delivery_planning = self.name

				so_wise_data = frappe.db.get_all("Delivery Planning Item",
												 {"related_delivey_planning": self.name,
												  "transporter": q.transporter,
												  "customer": q.customer,
												  "approved": "Yes"},
												 ["item_code",
												  "item_name",
												  "ordered_qty",
												  "weight_to_deliver",
												  "uom",
												  "conversion_factor",
												  "sorce_warehouse",
												  "sales_order"]
												 )
				print("0000000000000  000000000000000", so_wise_data)
				if (so_wise_data):
					for s in so_wise_data:
						pi.append("locations", {"item_code": s.item_code,
											"qty": s.ordered_qty,
											"uom": s.uom,
											"conversion_factor": s.conversion_factor,
											"warehouse": s.sorce_warehouse,
											"stock_qty": s.ordered_qty,
											"sales_order": s.sales_order
											})

				pi.save(ignore_permissions=True)
			return 1

	@frappe.whitelist()
	def make_dnote(self):
		salesno = 0
		discount = []
		transporter = ""
		print("********** In side Delivery Note ************")
		pl = frappe.db.get_all('Pick List',
							   filters={
       							 'docstatus': 1,
								 'related_delivery_planning': self.name },
							   fields= ['customer', 'name'])
		print("-----********-------",pl)
		if pl:
			for p in pl:
				dnote = frappe.new_doc('Delivery Note')
				dnote.customer = p.customer
				dnote.related_delivery_planning = self.name

				pli = frappe.db.get_all('Pick List Item',
										filters={ 'parent': p.name },
										fields =[ "item_code",
												  "qty",
												  'stock_uom',
												  "uom",
												  "conversion_factor",
												  "warehouse",
												  "sales_order"]
										)



				for p in pli:
					print("thisd is sales order --------", p.sales_order)
					salesno = p.sales_order
					dnote.append('items',{
									'item_code': p.item_code,
									'warehouse': p.warehouse,
									'qty': p.qty,
									'stock_qty': p.stock_qty,
									'uom': p.uom,

									'conversion_factor': p.conversion_factor,
									'against_sales_order': p.sales_order

								})
				discount = frappe.get_doc('Sales Order', salesno)
				print("p........p.........p", discount.additional_discount_percentage)
				print("---------- trans - -------------", discount.transporter)
				tax = frappe.get_list('Sales Taxes and Charges',
									  filters={'parent': salesno},
									  fields=["charge_type",
											  "account_head",
											  "description",
											  "rate"]
									  )
				print("--------- this  is taxes--------", tax)
				for t in tax:
					dnote.append('taxes',{
						'charge_type': t.charge_type,
						'description': t.description,
						'account_head': t.account_head,
						'rate': t.rate
					})


				dnote.tc_name = discount.tc_name
				dnote.additional_discount_percentage = discount.additional_discount_percentage
				dnote.apply_dicount_on = discount.apply_discount_on
				dnote.taxes_and_charges = discount.taxes_and_charges
				dnote.transporter = discount.transporter
				dnote.save(ignore_permissions=True)

				print('--------- Dnote ----  name ------------', dnote.name)

			return 1

		elif pl == []:
			# dpi = frappe.db.get_all('Delivery Planning Item',
			# 						filters={'related_delivey_planning': self.name,
			# 								  'approved': "Yes"},
			# 						group_by= 'customer','transporter',
			# 						fields = ['customer','transporter'])
			conditions = ""
			conditions += "AND related_delivey_planning = %s" % frappe.db.escape(self.name)
			dpi = frappe.db.sql(""" Select customer, transporter
							from `tabDelivery Planning Item`
							where approved = 'Yes'
							{conditions}
							Group By customer, transporter
							""".format(conditions=conditions), as_dict=1)
			print("**********", dpi)
			if dpi:
				for d in dpi:
					dnote = frappe.new_doc('Delivery Note')
					dnote.customer = d.customer
					dnote.related_delivery_planning = self.name
					dnote.transporter = d.transporter

					item = frappe.db.get_all('Delivery Planning Item',
											filters={'related_delivey_planning': self.name,
													 'approved': "Yes",
													 'supplier_dc': 0,
													 'customer': d.customer,
													 'transporter': d.transporter},
											fields= ["item_code",
													  "ordered_qty",
													  'stock_uom',
													  "uom",
													  "conversion_factor",
													  "sorce_warehouse",
													  "sales_order",
													  "name"]
											 )
					print(" */*/*/  */*/*/  /*/", item)

					for i in item:
						print("thisd is sales order --------", i.sales_order)
						salesno = i.sales_order
						dnote.append('items', {
							'item_code': i.item_code,
							'warehouse': i.sorce_warehouse,
							'qty': i.ordered_qty,
							'stock_qty': i.ordered_qty,
							'uom': i.uom,
							'stock_uom': i.stock_uom,
							'conversion_factor': i.conversion_factor,
							'against_sales_order': i.sales_order
						})

					discount = frappe.get_doc('Sales Order', salesno)
					print("p........p.........p", discount.additional_discount_percentage)

					tax = frappe.get_list('Sales Taxes and Charges',
										  filters={'parent': salesno},
										  fields=["charge_type",
												  "account_head",
												  "description",
												  "rate"]
										  )
					print("--------- this  is taxes--------", tax)
					for t in tax:
						dnote.append('taxes', {
							'charge_type': t.charge_type,
							'description': t.description,
							'account_head': t.account_head,
							'rate': t.rate
						})

					dnote.additional_discount_percentage = discount.additional_discount_percentage
					dnote.apply_dicount_on = discount.apply_discount_on
					dnote.taxes_and_charges = discount.taxes_and_charges
					dnote.tc_name = discount.tc_name
					# dnote.transporter = discount.transporter


					dnote.save(ignore_permissions=True)
					for i in item:
						newdoc = frappe.get_doc('Delivery Planning Item', i.name)
						newdoc.delivery_note = dnote.name
						newdoc.d_status = "Complete"
						newdoc.save(ignore_permissions=True)


				return 2

		else : return 0

	def before_cancel(self):
		print('This is before_cancel')
		dpi = frappe.get_all(doctype='Delivery Planning Item',
							  filters={"related_delivey_planning" : self.name})

		tdpi = frappe.get_all(doctype='Transporter Wise Planning Item',
							  filters={"related_delivery_planning" : self.name})

		popi = frappe.get_all(doctype='Purchase Orders Planning Item',
					   filters={"related_delivery_planning": self.name})

		if popi:
			for p in popi:
				popi = frappe.get_doc('Purchase Orders Planning Item', p.name)
				popi.delete()

		if tdpi:
			for t in tdpi:
				trans = frappe.get_doc('Transporter Wise Planning Item', t.name)
				trans.delete()

		if dpi:
			for d in dpi:
				ddpi = frappe.get_doc('Delivery Planning Item', d.name)
				ddpi.delete()

	@frappe.whitelist()
	def check_po_in_dpi(self):
		dpi_po = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={"approved": "Yes",
										  "transporter": "",
										  "related_delivey_planning": self.name,
										  })


		dpi_dn = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={"approved": "Yes",
										  "supplier_dc": 0,
										  "related_delivey_planning": self.name,
										  })

		if dpi_po and dpi_dn:
			return 1
		elif dpi_po :
			return 2
		elif dpi_dn :
			return 3
		else:
			return 0

	@frappe.whitelist()
	def check_transporter_po_btn(self):
		transporter = frappe.db.get_all(doctype='Transporter Wise Planning Item',
								   filters={
											"related_delivery_planning": self.name,
											})
		print("============== ==========",transporter)

		po = frappe.db.get_all(doctype='Purchase Orders Planning Item',
								   filters={
											"related_delivery_planning": self.name,
											})

		print("---------------------", po)

		if transporter and po:
			return 1
		elif transporter:
			return 2
		elif po:
			return 3
		else:
			return  0

	@frappe.whitelist()
	def check_dpi(self):
		print("Checking for dpisss -------- ------- ")
		dpi = frappe.db.get_all(doctype= 'Delivery Planning Item',
								 filters= {"related_delivey_planning": self.name })
		if not dpi:
			print("00000111111111122222222",dpi)
			return 1

	@frappe.whitelist()
	def refresh_status(self):
		a_count = count = 0

		if self.docstatus == 1:
			dpi_po = frappe.db.get_all(doctype='Delivery Planning Item',
									   filters={"approved": "Yes",
												"supplier_dc": 1,
												"related_delivey_planning": self.name,
												})
			print("--------------- dpi_po", len(dpi_po))

			dpi_dn = frappe.db.get_all(doctype='Delivery Planning Item',
									   filters={"approved": "Yes",
												"supplier_dc": 0,
												"related_delivey_planning": self.name,
												})
			print("--------------- dpi_pn", len(dpi_dn))

			dpi = frappe.db.get_all(doctype='Delivery Planning Item',
									filters={"related_delivey_planning": self.name})

			a_dpi_po = frappe.db.get_all(doctype='Delivery Planning Item',
									   filters={"approved": "Yes",
												"supplier_dc": 1,
												"related_delivey_planning": self.name,
												"d_status" : "Complete",
												})
			print("--------------- a_dpi_po", len(a_dpi_po))									
			# {"autoname": ["is", "not set"]}
			a_dpi_dn = frappe.db.get_all(doctype='Delivery Planning Item',
									   filters={"approved": "Yes",
												"supplier_dc": 0,
												"related_delivey_planning": self.name,
												"d_status" : 'Complete',
												})

			print("--------------- a_dpi_dn", len(a_dpi_dn))

			if dpi_dn and dpi_po:
				count = len(dpi_dn) + len(dpi_po)
			elif dpi_po:
				count = len(dpi_po)
			else:
				count = len(dpi_dn) 
			print("00000111111111122222222222222222", count)
			if a_dpi_dn and a_dpi_po:
				a_count = len(a_dpi_dn) + len(a_dpi_po)
			elif a_dpi_po:
				a_count = len(a_dpi_po)
			else:
				a_count = len(a_dpi_dn)
			print("00000111111111122222222333333333333", a_count)

			
			if count == a_count:
				self.db_set('d_status', "Completed", update_modified=False)
				print("------- in if 1 --------", count, a_count)
			elif count > 1 and count < len(dpi) :
				self.db_set('d_status', "Partially Planned", update_modified=False)
				print("------- in if 2  ---------", count, len(dpi))
			elif a_count == 0 and count > 0:
				self.db_set('d_status', "Planned and To Deliver & Order", update_modified=False)
				print("------- in if 3 ---------", count)
			elif len(a_dpi_po) > 0:
				self.db_set('d_status', "To Deliver", update_modified=False)
				print("------- in if 1 ---------", len(a_dpi_po))
			elif len(a_dpi_dn) > 0:
				self.db_set('d_status', "To Order", update_modified=False)
				print("------- in if 1 ---------", len(a_dpi_dn))
			else:
				self.db_set('d_status', "Pending Planning", update_modified=False)
				print("------- in if PP1 ---------", count)

			# self.save(ignore_permissions=True)
			return 1


