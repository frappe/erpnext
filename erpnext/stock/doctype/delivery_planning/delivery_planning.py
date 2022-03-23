# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import date

class DeliveryPlanning(Document):
	# def on_submit(self):
	# 	self.on_delivery_planning_submit()

	@frappe.whitelist()
	def refresh_page(self):
		self.reload()

	@frappe.whitelist()	
	def on_delivery_planning_submit(self):
		conditions = ""
		pinc = ""
		if self.company:
			conditions += "AND so.company = %s" % frappe.db.escape(self.company)

		if self.transporter:
			conditions += "AND so.transporter = %s" % frappe.db.escape(self.transporter)

		if self.delivery_date_from and self.delivery_date_to:
			# conditions += "AND soi.delivery_date >= '%s'" % self.delivery_date_from
			from_date = self.delivery_date_from
			to_date = self.delivery_date_to 
			# conditions += "and soi.delivery_date between %(from_date)s and %(to_date)s"
		# if self.delivery_date_to:
		# 	conditions += "AND soi.delivery_date <= '%s'" % self.delivery_date_to

		if self.pincode_from:
			pincodefrom = self.pincode_from
		
		if self.pincode_to:
			pincodeto = self.pincode_to

		if(self.pincode_from and self.pincode_to):
			pin = frappe.db.sql("""Select dl.link_name from `tabDynamic Link` as dl,
								`tabAddress` as a
								where dl.parent = a.name
								and dl.parenttype = "Address" 
								and dl.link_doctype = "Customer"
								and a.pincode between {pinfrom} and {pinto} 
								""".format( pinfrom = pincodefrom, pinto = pincodeto), as_dict= 1)	
			if pin:
				count = len(pin)
				ct =0 
				for p in pin:
					pinc += '"'+ p.link_name +'"'
					ct += 1
					if ct != count:
						pinc += ","

				conditions += " AND so.customer in ({0})".format(pinc)			

		query = frappe.db.sql(""" select
									so.customer,
									soi.name as dname,
									soi.item_code,
									soi.item_name,
									soi.warehouse,
									soi.qty,
									soi.rate,
									soi.stock_qty,
									so.name,
									soi.name as soi_item,
									soi.weight_per_unit,
									soi.delivery_date,
									soi.projected_qty,
									soi.actual_qty,
									so.transporter,
									soi.delivered_by_supplier,
									soi.supplier,
									soi.uom,
									soi.conversion_factor,
									soi.stock_uom,
									soi.delivered_qty,
									a.pincode

									from `tabSales Order Item` soi
									join `tabSales Order` so ON soi.parent = so.name
									Left join `tabAddress` a  ON so.customer = a.address_title

									where so.docstatus = 1
									and so.status IN ("To Deliver" , "To Deliver and Bill")
                                    and so.delivery_status NOT IN ("Fully Delivered","Closed")	
									and soi.delivery_date between '{0}' and '{1}' 									
									and (soi.qty - soi.delivered_qty ) != 0
									{conditions} """.format(from_date, to_date, conditions=conditions), as_dict=1)
		for i in query:
			dp_item = frappe.new_doc("Delivery Planning Item")
			if i.delivered_by_supplier == 0:
				dp_item.transporter = i.transporter
				
			dp_item.customer = i.customer
			dp_item.item_code = i.item_code
			# dp_item.item_name = i.item_name
			dp_item.item_dname = i.dname
			dp_item.rate = i.rate
			if i.delivered_qty > 0:
				dp_item.ordered_qty = abs(i.qty - i.delivered_qty)
				dp_item.pending_qty = 0
				dp_item.qty_to_deliver = abs(i.qty - i.delivered_qty)
				dp_item.weight_to_deliver = i.weight_per_unit * i.qty
			else:
				dp_item.ordered_qty = i.qty
				dp_item.pending_qty = 0
				dp_item.qty_to_deliver = i.qty
				dp_item.weight_to_deliver = i.weight_per_unit * i.qty
	
			dp_item.sales_order = i.name
			dp_item.sorce_warehouse = i.warehouse
			dp_item.postal_code = i.pincode
			dp_item.delivery_date = i.delivery_date
			dp_item.related_delivey_planning = self.name
			dp_item.weight_per_unit = i.weight_per_unit
			dp_item.supplier_dc = i.delivered_by_supplier
			dp_item.supplier = i.supplier
			dp_item.planned_date = i.delivery_date
			dp_item.conversion_factor = i.conversion_factor
			dp_item.stock_uom = i.stock_uom
			dp_item.insert(ignore_mandatory=True)
			# dp_item.save(ignore_permissions = True);
			dp_item.reload()
			
			docs = frappe.db.get_all(doctype='Bin',
							filters={"warehouse": i.warehouse,
									"item_code": i.item_code},
							fields= ["projected_qty","actual_qty"])
			
			if docs:
				for d in docs:
					
					frappe.db.set_value('Delivery Planning Item', dp_item.name, {
									'current_stock': d.projected_qty,
									'available_stock':  d.actual_qty
										})
					# dp_item.current_stock = d.projected_qty
						# dp_item.available_stock = d.actual_qty
			dp_item.reload()		


		self.reload()	
		if query:	
			frappe.msgprint(
			msg='Delivery Planning Item Created',
			title='Success')

		# self.reload()
		return 1

	# on click of custom button Calculate Purchase Order Plan Summary create new PODPI
	@frappe.whitelist()
	def purchase_order_call(self):
		item = frappe.get_all(doctype='Delivery Planning Item',
							  filters={
									   "supplier_dc": 1,
									   "docstatus" : 1,
									   "related_delivey_planning" : self.name})
		if(item):

			for i in item:

				popi = frappe.db.get_all(doctype= 'Purchase Orders Planning Item',
										 filters={"related_delivery_planning" : self.name})


				if popi:
					for p in popi:
						frappe.db.delete('Purchase Orders Planning Item', {
							'name': p.name
						})
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

									where supplier_dc = 1 and docstatus = 1
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

											where supplier_dc = 1 and docstatus = 1
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
		item = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={
										  "supplier_dc": 0,
										  "docstatus" :1,
										  "related_delivey_planning": self.name})

		if (item):
			for i in item:
				popi = frappe.db.get_all(doctype='Transporter Wise Planning Item',
										 filters={"related_delivery_planning": self.name})

				if popi:
					for p in popi:
						frappe.db.delete('Transporter Wise Planning Item', {
							'name': p.name
						})
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

											where supplier_dc = 0
											AND docstatus = 1
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
														 
														  "docstatus" : 1,
														  "supplier_dc" : 0},
														 ["sales_order","item_name","item_code","customer",
														  "ordered_qty","weight_to_deliver"]
														 )
						if(so_wise_data):
							for s in so_wise_data:
								dp_item.append("items",{"sales_order": s.sales_order,
														"item_code":s.item_code,
														"item_name": s.item_name,
														"qty": s.ordered_qty,
														"weight": s.weight_to_deliver,
														"customer": s.customer,
														"item_code": s.item_code
														})
						dp_item.save(ignore_permissions=True)

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

										where docstatus = 1
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
														 "docstatus" : 1
														  },
														 ["sales_order", "item_name", "ordered_qty",
														  "weight_to_deliver","item_code","customer"]
														 )
						if (so_wise_data):
							for s in so_wise_data:
								dp_item.append("items", {"sales_order": s.sales_order,
														 "item_name": s.item_name,
														 "qty": s.ordered_qty,
														 "weight": s.weight_to_deliver,
														 "customer": s.customer,
														 "item_code": s.item_code
														 })

						dp_item.related_delivery_planning = self.name
						dp_item.save(ignore_permissions=True)
			self.reload()
			return 1

		else:
			return 0

	@frappe.whitelist()
	def make_po(self):
		salesno = 0
		discount = []
		item = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={
										  "supplier_dc": 1,
										  "docstatus" : 1,
										  "related_delivey_planning": self.name})
		if (item):
			for i in item:
				conditions = ""
				conditions += "AND dpi.related_delivey_planning = %s" % frappe.db.escape(self.name)
				query = frappe.db.sql(""" select
										dpi.supplier,
										sum(dpi.ordered_qty) t_qty,
										sum(dpi.weight_to_deliver) t_weight

										from `tabDelivery Planning Item`dpi

										where dpi.supplier_dc = 1
										
										AND dpi.docstatus = 1
										AND dpi.purchase_order IS NULL

										{conditions}
										group by dpi.supplier
										""".format(conditions=conditions), as_dict=1)

			if query:
				for q in query:
					po = frappe.new_doc("Purchase Order")
					po.supplier = q.supplier
					po.total_qty = q.t_qty
					po.total_net_weight = q.t_weight
					po.related_delivery_planning = self.name

					so_wise_data = frappe.db.get_all("Delivery Planning Item",
													{"related_delivey_planning": self.name,
													"supplier": q.supplier,
													},
													["item_code",
													"item_name",
													"ordered_qty",
													"delivery_date",
													"sorce_warehouse",
													"sales_order",
													"item_dname",
													"name",
													"docstatus",
													"qty_to_deliver"
													]
													)
					if (so_wise_data):
						for s in so_wise_data:
							salesno = s.sales_order
							po.append("items", {"item_code": s.item_code,
												"item_name": s.item_name,
												"schedule_date":s.delivery_date,
												"qty": s.ordered_qty,
												"warehouse": s.sorce_warehouse,
												"sales_order": s.sales_order,
												"delivered_by_supplier" : 1,
												"sales_order_item" : s.item_dname
												})

					discount = frappe.get_doc('Sales Order', salesno)
					po.save(ignore_permissions=True)
					po.submit()
					# po.save()
					# frappe.db.commit()
					for i in so_wise_data:
							frappe.db.set_value('Delivery Planning Item', i.name,
							{'purchase_order' : po.name,
							'd_status' : "Complete",
							})

							frappe.db.set_value('Sales Order Item', i.item_dname, {
							'delivered_qty': i.qty_to_deliver,
							'ordered_qty' : i.ordered_qty,
							# 'actual_qty' : i.available_stock, 
							#'projected_qty' : i.current_stock,
							},  update_modified=False)	

				return 1

	@frappe.whitelist()
	def make_picklist(self):
		item = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={
										  "supplier_dc": 0,
										  "docstatus" : 1,
										  "related_delivey_planning": self.name,
										  },
								fields = ["name","pick_list"])
		if (item):
			conditions = ""
			conditions += "AND dpi.related_delivey_planning = %s" % frappe.db.escape(self.name)
			query = frappe.db.sql(""" select
									transporter,
									customer,
									sum(dpi.weight_to_deliver) t_weight

									from `tabDelivery Planning Item`dpi

									where dpi.supplier_dc = 0
									
									AND dpi.transporter IS NOT NULL
									AND dpi.docstatus = 1
									AND dpi.pick_list IS NULL
									{conditions}
									group by dpi.transporter, dpi.customer
									""".format(conditions=conditions), as_dict=1)
			for q in query:
				pi = frappe.new_doc("Pick List")
				pi.customer = q.customer
				pi.purpose = "Delivery"
				pi.related_delivery_planning = self.name

				so_wise_data = frappe.db.get_all("Delivery Planning Item",
												 {"related_delivey_planning": self.name,
												  "transporter": q.transporter,
												  "customer": q.customer,
												  
												  "docstatus":1},
												 ["item_code",
												  "item_name",
												  "ordered_qty",
												  "weight_to_deliver",
												  "uom",
												  "conversion_factor",
												  "sorce_warehouse",
												  "sales_order",
												  "docstatus",
												  "name"]
												 )
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
						frappe.db.set_value('Delivery Planning Item', s.name,
						{'pick_list' : pi.name,})					
				pi.save(ignore_permissions=True)
				pi.submit()
				for i in item:
						frappe.db.set_value('Delivery Planning Item', i.name,
						{'pick_list' : pi.name,
						})
				
			return 1

	@frappe.whitelist()
	def make_dnote(self):
		item = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={
										  "supplier_dc": 0,
										  "docstatus" : 1,
										  "related_delivey_planning": self.name,
										  })
		salesno = ""
		discount = []
		transporter = ""
		pick_list = ""
		# pl = frappe.db.get_all('Pick List',
		# 					   filters={
       	# 						 'docstatus': 1,
		# 						 'related_delivery_planning': self.name },
		# 					   fields= ['customer', 'name'])
		# if pl:
		# 	for p in pl:
		# 		dnote = frappe.new_doc('Delivery Note')
		# 		dnote.customer = d.customer
		# 		dnote.related_delivery_planning = self.name
		# 		dnote.transporter = d.transporter

		# 		item = frappe.db.get_all('Delivery Planning Item',
		# 								filters={'related_delivey_planning': self.name,
												
		# 										'supplier_dc': 0,
		# 										'customer': d.customer,
		# 										'transporter': d.transporter},
		# 								fields= ["item_code",
		# 										"ordered_qty",
		# 										'stock_uom',
		# 										"uom",
		# 										"current_stock",
		# 										"available_stock",
		# 										"conversion_factor",
		# 										"sorce_warehouse",
		# 										"sales_order",
		# 										"name",
		# 										"pick_list",
		# 										"docstatus",
		# 										"item_dname",
		# 										"qty_to_deliver"]
		# 								)

		# 		for i in item:
		# 			if(i.pick_list):
		# 				pick_list = i.pick_list
		# 			salesno = i.sales_order
		# 			dnote.append('items', {
		# 				'item_code': i.item_code,
		# 				'warehouse': i.sorce_warehouse,
		# 				'qty': i.qty_to_deliver,
		# 				'stock_qty': i.qty_to_deliver,
		# 				'uom': i.uom,
		# 				'stock_uom': i.stock_uom,
		# 				'conversion_factor': i.conversion_factor,
		# 				'against_sales_order': i.sales_order
		# 			})

					

		# 		discount = frappe.get_doc('Sales Order', salesno)
		# 		tax = frappe.get_list('Sales Taxes and Charges',
		# 							  filters={'parent': salesno},
		# 							  fields=["charge_type",
		# 									  "account_head",
		# 									  "description",
		# 									  "rate"]
		# 							  )
		# 		if discount.additional_discount_percentage:
		# 				dnote.additional_discount_percentage = discount.additional_discount_percentage
		# 		if discount.apply_discount_on:	
		# 			dnote.apply_dicount_on = discount.apply_discount_on

		# 		if discount.taxes_and_charges:
		# 			dnote.taxes_and_charges = discount.taxes_and_charges

		# 		if discount.tc_name:	
		# 			dnote.tc_name = discount.tc_name

		# 		if discount.transporter:	
		# 			dnote.transporter = discount.transporter

		# 		for i in item:
		# 			dpi = frappe.get_doc("Delivery Planning Item",i.get("name"))
		# 			if(i.get("name") != "DPI-21-08-00075"):
		# 				dnote.append("items",{
		# 					"item_code" : dpi.get("item_code"),
		# 					"qty":dpi.get("qty_to_deliver")
		# 				})
		# 			frappe.db.set_value('Delivery Planning Item', i.name,
		# 								{'delivery_note' : dnote.name,
		# 									'd_status' : "Complete"})
		# 			frappe.db.commit()
		# 		dnote._action = "save"
		# 		dnote.validate()
		# 		dnote.insert()

		# 	return 1

		# elif pl == []:
		conditions = ""
		conditions += "AND related_delivey_planning = %s" % frappe.db.escape(self.name)
		dpi = frappe.db.sql(""" Select name, customer, transporter
						from `tabDelivery Planning Item`
						where docstatus = 1 AND supplier_dc = 0 AND d_status != "Complete"
						{conditions}
						Group By customer, transporter, delivery_date
						""".format(conditions=conditions), as_dict=1)
		if dpi:
			for d in dpi:
				dnote = frappe.new_doc('Delivery Note')
				dnote.customer = d.customer
				dnote.related_delivery_planning = self.name
				dnote.transporter = d.transporter

				t_name = frappe.db.get_value('Supplier', d.transporter, 'supplier_name')
				dnote.transporter_name = t_name

				item = frappe.db.get_all('Delivery Planning Item',
										filters={'related_delivey_planning': self.name,
													'supplier_dc': 0,
													'customer': d.customer,
													'transporter': d.transporter,
													'docstatus' :1,
													'd_status':  "Incomplete"},
										fields= ["item_code",
													"ordered_qty",
													'stock_uom',
													"uom",
													"conversion_factor",
													"sorce_warehouse",
													"sales_order",
													"name",
													"pick_list",
													"item_dname",
													"qty_to_deliver",
													"docstatus",
													"batch_no",
													"item_dname"]
											)

				for i in item:
					if(i.pick_list):
						pick_list = i.pick_list
					salesno = i.sales_order
					# so_item = {}
					if i.item_dname:
						so_item = frappe.get_doc("Sales Order Item", i.item_dname)

						if i.batch_no:
							dnote.append('items', {
							'item_code': i.item_code,
							'warehouse': i.sorce_warehouse,
							'qty': i.qty_to_deliver,
							'stock_qty': i.qty_to_deliver,
							'uom': so_item.uom,
							'rate': so_item.rate,
							'stock_uom': so_item.stock_uom,
							'conversion_factor': i.conversion_factor,
							'against_sales_order': i.sales_order,
							'batch_no' : i.batch_no
							})
						else:	
							dnote.append('items', {
								'item_code': i.item_code,
								'warehouse': i.sorce_warehouse,
								'qty': i.qty_to_deliver,
								'stock_qty': i.qty_to_deliver,
								'uom': so_item.uom,
								'rate': so_item.rate,
								'stock_uom': so_item.stock_uom,
								'conversion_factor': i.conversion_factor,
								'against_sales_order': i.sales_order
							})

					else: 
							dnote.append('items', {
							'item_code': i.item_code,
							'warehouse': i.sorce_warehouse,
							'qty': i.qty_to_deliver,
							'stock_qty': i.qty_to_deliver,
							'uom': i.uom,
							'rate': i.rate,
							'stock_uom': i.stock_uom,
							'conversion_factor': i.conversion_factor,
							'against_sales_order': i.sales_order
						})	

				discount = frappe.get_doc('Sales Order', salesno)

				if discount.additional_discount_percentage:
					dnote.additional_discount_percentage = discount.additional_discount_percentage

				if discount.apply_discount_on:	
					dnote.apply_dicount_on = discount.apply_discount_on

				if discount.taxes_and_charges:
					dnote.taxes_and_charges = discount.taxes_and_charges

				
				if discount.tc_name:	
					dnote.tc_name = discount.tc_name

				
				if discount.transporter:	
					dnote.transporter = discount.transporter

				
				if pick_list:
					dnote.pick_list = pick_list

				# dnote.save(ignore_permissions=True)
				# dnote.submit()
				
				dnote._action = "save"
				dnote.validate()
				dnote.insert()
				auto_submit = frappe.db.get_single_value('Stock Settings', 'dn_auto_submit')
				if auto_submit == "Yes":
					dnote.submit()

				for i in item:
					frappe.db.set_value('Delivery Planning Item', i.name,
										{'delivery_note' : dnote.name,
										'd_status' : "Complete"})
					frappe.db.commit()

					frappe.db.set_value('Sales Order Item', i.item_dname, {
							'delivered_qty': i.qty_to_deliver,
							'ordered_qty' : i.ordered_qty,
							# 'actual_qty' : i.available_stock, 
							#'projected_qty' : i.current_stock,
							},  update_modified=False)	
					frappe.db.commit()				
			return 2

		else : return 0

	def before_cancel(self):
		dpi = frappe.get_all(doctype='Delivery Planning Item',
							  filters={"related_delivey_planning" : self.name})
		if(dpi):
			for d in dpi:	
				doc = frappe.get_doc('Delivery Planning Item', d.name)	
				doc.cancel()	

			return 1 	
  
	def before_cancel(self):
		dpi = frappe.get_all(doctype='Delivery Planning Item',
							  filters={"related_delivey_planning" : self.name},fields=['*'])

		if dpi:
			for i in dpi:

				if i.qty_to_deliver:
					delivered_qty = frappe.db.get_value('Sales Order Item', i.item_dname,'delivered_qty')
					delivered_qty -= i.qty_to_deliver
					frappe.db.set_value('Sales Order Item', i.item_dname, {
									'delivered_qty': delivered_qty
									},  update_modified=False)	

		tdpi = frappe.get_all(doctype='Transporter Wise Planning Item',
							  filters={"related_delivery_planning" : self.name})

		popi = frappe.get_all(doctype='Purchase Orders Planning Item',
					   filters={"related_delivery_planning": self.name})

		if popi:
			for p in popi:
				pop = frappe.get_doc('Purchase Orders Planning Item', p.name)
				pop.delete()

		if tdpi:
			for t in tdpi:
				trans = frappe.get_doc('Transporter Wise Planning Item', t.name)
				trans.delete()

	@frappe.whitelist()
	def check_po_in_dpi(self):
		dpi_po = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={
								 		  "supplier_dc": 1, 
										  "docstatus" : 1,
										  "related_delivey_planning": self.name,
										  })


		dpi_dn = frappe.db.get_all(doctype='Delivery Planning Item',
								 filters={
										  "supplier_dc": 0,
										  "docstatus" : 1,
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

		po = frappe.db.get_all(doctype='Purchase Orders Planning Item',
								   filters={
											"related_delivery_planning": self.name,
											})

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
		dpi = frappe.db.get_all(doctype= 'Delivery Planning Item',
								 filters= {"related_delivey_planning": self.name })
		if not dpi:
			return 1

	@frappe.whitelist()
	def refresh_status(self):
		a_count = count = 0

		if self.docstatus == 1:
			dpi_po = frappe.db.get_all(doctype='Delivery Planning Item',
									   filters={
												"supplier_dc": 1,
												"docstatus": 1,
												"related_delivey_planning": self.name,
												})
			dpi_dn = frappe.db.get_all(doctype='Delivery Planning Item',
									   filters={
												"supplier_dc": 0,
												"docstatus": 1,
												"related_delivey_planning": self.name,
												})

			dpi = frappe.db.get_all(doctype='Delivery Planning Item',
									filters={"related_delivey_planning": self.name})

			a_dpi_po = frappe.db.get_all(doctype='Delivery Planning Item',
									   filters={
												"supplier_dc": 1,
												"related_delivey_planning": self.name,
												"d_status" : "Complete",
												"docstatus":1,
												})									
			# {"autoname": ["is", "not set"]}
			a_dpi_dn = frappe.db.get_all(doctype='Delivery Planning Item',
									   filters={
												"supplier_dc": 0,
												"related_delivey_planning": self.name,
												"d_status" : 'Complete',
												"docstatus": 1,
												})									

			if dpi_dn and dpi_po:
				count = len(dpi_dn) + len(dpi_po)
			elif dpi_po:
				count = len(dpi_po)
			else:
				count = len(dpi_dn) 
			if a_dpi_dn and a_dpi_po:
				a_count = len(a_dpi_dn) + len(a_dpi_po)
			elif a_dpi_po:
				a_count = len(a_dpi_po)
			else:
				a_count = len(a_dpi_dn)
			
			if count == a_count and count > 0:
				self.db_set('d_status', "Completed", update_modified=False)
			elif count > 1 and count < len(dpi) :
				self.db_set('d_status', "Partially Planned", update_modified=False)
			elif a_count == 0 and count > 0:
				self.db_set('d_status', "Planned and To Deliver & Order", update_modified=False)
			elif len(a_dpi_po) > 0:
				self.db_set('d_status', "To Deliver", update_modified=False)
			elif len(a_dpi_dn) > 0: 
				self.db_set('d_status', "To Order", update_modified=False)
			else:
				self.db_set('d_status', "Pending Planning", update_modified=False)

			# self.save("update")
			return 1


