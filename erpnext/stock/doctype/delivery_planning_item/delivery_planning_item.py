# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from bs4.element import Doctype
import frappe
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import update_child_qty_rate
from datetime import date

class DeliveryPlanningItem(Document):

	def before_submit(self):
		if not self.transporter and not self.supplier:
			frappe.throw("Please select Transporter or Supplier")

		if self.qty_to_deliver >= self.available_stock:
			frappe.throw(" Cannot submit, current warehouse doesn't have sufficient stock for item {0}".format(self.item_code))		


	def before_save(self):
		if not self.is_new() :
			old_doc = self.get_doc_before_save()
			if old_doc.sorce_warehouse != self.sorce_warehouse or old_doc.qty_to_deliver != self.qty_to_deliver or old_doc.supplier != self.supplier:
			# price changed
				self.is_updated =1

		if self.docstatus != 1 and self.supplier_dc == 0:
			frappe.db.set_value('Delivery Planning Item', self.name, {
				'supplier' : "",
				'supplier_name' : ""
			})
		elif self.docstatus != 1  and self.supplier_dc == 1:
			frappe.db.set_value('Delivery Planning Item', self.name, {
				'transporter' : "",
				'transporter_name' : ""
			})	
						
	
	def on_submit(self):
		
		newname = ""
		if self.is_split == 1:
			# code to add split item SOI of SO
			
			# retriving info from DPI used to split
			pdpi = frappe.get_doc('Delivery Planning Item', self.sd_item)
		

			# SOI used in split and updating the SOI
			ref_soi = frappe.get_doc('Sales Order Item', self.split_from_item)
			
			frappe.db.set_value('Sales Order Item', self.split_from_item,
						{'qty' : pdpi.qty_to_deliver,
						'stock_qty' : pdpi.qty_to_deliver,
						'amount' : pdpi.qty_to_deliver * ref_soi.rate,
						})		

			# getting length soi for sales order child table items for IDX of new SOI
			sos = frappe.get_all(doctype = 'Sales Order Item', filters={ 'parent': self.sales_order})

			# creating new SOI for splitted DPI
			soi = frappe.new_doc('Sales Order Item')
			soi.stock_qty = self.qty_to_deliver
			soi.idx = len(sos)+1
			soi.rate = ref_soi.rate
			soi.amount = ref_soi.rate * self.qty_to_deliver
			soi.parentfield = "items"
			soi.docstatus = 1
			soi.item_name = self.item_name
			soi.description = ref_soi.description
			soi.parent = self.sales_order
			soi.parenttype = "Sales Order"
			soi.item_code = self.item_code
			soi.delivery_date = self.delivery_date	
			soi.qty = self.qty_to_deliver
			soi.delivered_by_supplier = self.supplier_dc
			soi.supplier = self.supplier
			soi.uom = ref_soi.uom
			soi.warehouse = self.sorce_warehouse
			soi.conversion_factor = ref_soi.conversion_factor
			# soi.save(ignore_permissions=True)
			soi._action = "save"
			soi.insert()

			# so = frappe.get_doc("Sales Order", self.sales_order)
			# so.validate()

			newname = soi.name
			
			# setting new soi ID to split DPI
			frappe.db.set_value('Delivery Planning Item', self.name, 'item_dname', newname)
			frappe.db.commit()

			if soi:
				frappe.msgprint(
					msg='Sales Order Item {soi} added in Sales Order {so}'.format(soi = soi.name, so = self.sales_order),
					title='Approval message',
				)

		if self.is_updated == 1 and self.is_split == 0:
			# IF doc is updated then pusing same updates on SOI 

			ref_soi = frappe.db.set_value('Sales Order Item', self.item_dname, {
					# "qty" : self.qty_to_deliver,
					# "stock_qty" : self.qty_to_deliver,
					# "amount" : self.qty_to_deliver * self.rate,
					"delivered_by_supplier" : self.supplier_dc,
					"supplier" : self.supplier,
					"warehouse" : self.sorce_warehouse
				})
			# ref_soi = frappe.get_doc('Sales Order Item', self.item_dname)
			# ref_soi.qty = self.qty_to_deliver,
			# ref_soi.stock_qty = self.qty_to_deliver,
			# ref_soi.amount = self.qty_to_deliver * self.rate
			# ref_soi.delivered_by_supplier = self.supplier_dc
			# ref_soi.supplier = self.supplier
			# ref_soi.save(ignore_permissions=True)
			
			if(ref_soi):
				frappe.msgprint(
					msg='Sales Order Item {soi} added in Sales Order {so}'.format(soi = soi.name, so = self.sales_order),
					title='Approval message',
				)
		
	@frappe.whitelist()
	def split_dp_item(self,n_transporter, n_qty, n_src_warehouse,n_supplier_dc, n_supplier, n_date):
		new_qty = 0
		siname = ""
		sidesc = ""
		sname = ""
		sirate = 0
		if(n_transporter, n_supplier, n_src_warehouse, n_qty):
			if n_qty != self.ordered_qty:
				new_qty = int(self.ordered_qty) - n_qty

				# updateing old dpi 
				frappe.db.set_value('Delivery Planning Item', self.name, {
					'ordered_qty': new_qty,
					'pending_qty': 0,
					'qty_to_deliver': new_qty,
					'weight_to_deliver': float(new_qty) * float(self.weight_per_unit),

				})
		
			# soi1 = frappe.db.sql(""" Select name, item_code, item_name, rate, description 
			# 						from `tabSales Order Item` where name = '{0}'
			# 						""".format(self.item_dname),as_dict=1)
			# print("----------s01 ============",soi1)															
			
			# if soi1:
			# 	for s in soi1:
			# 		sidesc = s.description
			# 		siname = s.item_name 	
			# 		sirate = s.rate	
			# 		sname = s.name	
			# 		sitem_code = s.item_code
							
			# print("----------======= name, desc -----=========",sidesc , siname,sname, sirate)
			
			# if (n_transporter):
			# 	frappe.db.set_value('Sales Order', self.sales_order, 'transporter', n_transporter)

			# creating new DPI after split
			dp_item = frappe.new_doc("Delivery Planning Item")
			if(n_supplier_dc == 0):
				dp_item.transporter = n_transporter

			dp_item.customer = self.customer
			dp_item.item_code = self.item_code
			dp_item.item_name = self.item_name
			dp_item.ordered_qty = n_qty
			dp_item.pending_qty = 0
			dp_item.qty_to_deliver = n_qty
			dp_item.weight_to_deliver = float(self.weight_per_unit) * n_qty
			dp_item.sales_order = self.sales_order
			dp_item.sorce_warehouse = n_src_warehouse
			dp_item.postal_code = self.postal_code
			dp_item.delivery_date = self.delivery_date
			dp_item.planned_date = n_date
			dp_item.current_stock = self.current_stock
			dp_item.available_stock = self.available_stock
			dp_item.related_delivey_planning = self.related_delivey_planning
			dp_item.weight_per_unit = self.weight_per_unit
			dp_item.supplier_dc = n_supplier_dc
			dp_item.supplier = n_supplier
			dp_item.uom = self.uom
			dp_item.batch_no=self.batch_no
			dp_item.conversion_factor = self.conversion_factor
			dp_item.is_split = 1
			dp_item.split_from_item = self.item_dname
			dp_item.sd_item = self.name
			dp_item.stock_uom = n_qty
			dp_item.insert(ignore_mandatory=True)
			# dp_item.save(ignore_permissions=True)

			return 1
		else: return 0

	@frappe.whitelist()
	def update_stock(self):	
		docs = frappe.db.get_all(doctype='Bin',
								filters={"warehouse": self.sorce_warehouse,
										"item_code": self.item_code},
								fields= ["projected_qty","actual_qty"])
		print(" ITEM CODE", docs, self.item_code)						

		if docs:
			for doc in docs:	
				if(doc.projected_qty == 0 or doc.actual_qty == 0):
					
					frappe.db.sql("""UPDATE `tabDelivery Planning Item` 
					SET current_stock = 0,
					available_stock = 0
					WHERE name = {0} """.format("'"+self.name+"'"))
					frappe.throw(
						title='Error',
						msg='Selected Warehouse does not have stock'
						)
				else:	
					
					frappe.db.sql("""UPDATE `tabDelivery Planning Item` 
					SET current_stock = {0},
					available_stock = {1}
					WHERE name = {2} """.format(doc.projected_qty, doc.actual_qty, "'"+self.name+"'"))	

					return doc	

		else:
			frappe.throw(
						title='Error',
						msg='Selected Warehouse does not have stock'
						)
				# frappe.db.set_value('Delivery Planning Item', self.name, {
				# 		'available_stock' : doc.actual_qty,
				# 		'current_stock' : doc.projected_qty
				# 	})
		# self.save()
					

@frappe.whitelist()
def approve_function(source_names):
	names = list(source_names.split(","))
	for name in names:
		x = name.translate({ord(i): None for i in ']"['})
		doc = frappe.get_doc('Delivery Planning Item', x)
		if doc.approved:
			frappe.msgprint(
				msg='Approval status for planning item {item} is already set to {approve}'.format(item = doc.name, approve = doc.approved),
				title='Approval message',
			)
		else:
			doc.approved = 'Yes'
			doc.save()
			frappe.msgprint(
				msg='Plannig item {item} Approved'.format(item = doc.name),
				title='Approval message',
			)
			
	return 1

# reject_function
@frappe.whitelist()
def reject_function(source_names):
	names = list(source_names.split(","))
	for name in names:
		x = name.translate({ord(i): None for i in ']"['})
		doc = frappe.get_doc('Delivery Planning Item', x)
		if doc.approved == "": 
			doc.approved = 'No'
			doc.save()			
			frappe.msgprint(
				msg='Plannig item {item} Rejected'.format(item = doc.name),
				title='Rejection message',
			)
		else:
			frappe.msgprint(
				msg='Approval status for planning item {item} is already set to {approve}'.format(item = doc.name, approve = doc.approved),
				title='Rejection message',
			)
			
	return 1	

# split_function
@frappe.whitelist()
def split_function(source_names, n_transporter, n_qty, n_src_warehouse, n_supplier_dc, n_supplier, n_date, batch_no):
	dpi = ""
	names = list(source_names.split(","))
	for name in names:
		x = name.translate({ord(i): None for i in ']"['})
		doc = frappe.get_doc('Delivery Planning Item', x)

	new_qty = 0
	siname = ""
	sidesc = ""
	sname = ""
	sirate = 0
	newname = ""
	if(n_qty):
		if n_qty != doc.ordered_qty:
			new_qty = float(doc.ordered_qty) - float(n_qty)
			n_weight = float(doc.weight_per_unit) * float(n_qty)
			

			n_weight = float(doc.weight_per_unit) * new_qty
			# update old dpi 
			frappe.db.set_value('Delivery Planning Item', doc.name, {
				'ordered_qty': new_qty,
				'pending_qty': new_qty,
				'qty_to_deliver': new_qty,
				'weight_to_deliver': float(new_qty) * float(doc.weight_per_unit)
			})
		dp_item = frappe.new_doc("Delivery Planning Item")
		# dp_item.item_dname = newname
		if n_transporter :
			dp_item.transporter = n_transporter
		
		if n_supplier :
			dp_item.suppier = n_supplier

		dp_item.customer = doc.customer
		dp_item.rate = doc.rate
		dp_item.item_code = doc.item_code
		dp_item.item_name = doc.item_name
		dp_item.ordered_qty = n_qty
		dp_item.pending_qty = 0
		dp_item.qty_to_deliver = n_qty
		dp_item.weight_to_deliver = float(doc.weight_per_unit) * float(n_qty)
		dp_item.sales_order = doc.sales_order
		dp_item.sorce_warehouse = n_src_warehouse
		dp_item.postal_code = doc.postal_code
		dp_item.delivery_date = doc.delivery_date
		dp_item.planned_date = n_date
		dp_item.current_stock = doc.current_stock
		dp_item.available_stock = doc.available_stock
		dp_item.related_delivey_planning = doc.related_delivey_planning
		dp_item.weight_per_unit = doc.weight_per_unit
		dp_item.supplier_dc = n_supplier_dc
		dp_item.supplier = n_supplier
		dp_item.uom = doc.uom
		dp_item.conversion_factor = doc.conversion_factor
		dp_item.is_split = 1
		dp_item.split_from_item = doc.item_dname
		dp_item.sd_item = doc.name
		dp_item.stock_uom = n_qty
		dp_item.batch_no = batch_no
		dp_item.insert(ignore_mandatory=True)
		# dp_item.save(ignore_permissions=True)

	return 1
