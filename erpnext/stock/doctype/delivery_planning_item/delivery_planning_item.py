# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DeliveryPlanningItem(Document):

	# @frappe.whitelist()
	# def d_status_update(self, dname):
	# 	doc = frappe.get_doc("Delivery Planning Item", 'dname')
	# 	doc.d_status = "Complete"
	# 	doc.save(ignore_permissions=True)

	@frappe.whitelist()
	def split_dp_item(self,n_transporter, n_qty, n_src_warehouse, n_supplier, n_date):
		new_qty = 0
		if(n_transporter, n_supplier, n_src_warehouse, n_qty):
			if n_qty != self.ordered_qty:
				new_qty = int(self.ordered_qty) - n_qty
				print("------- per unit ---------- ",self.weight_per_unit,"-------- new Qty ------- ", n_qty)
				n_weight = self.weight_per_unit * n_qty
				print("===== new n weight ===== ", n_weight)
				dp_item = frappe.new_doc("Delivery Planning Item")
				dp_item.transporter = n_transporter
				dp_item.customer = self.customer
				dp_item.item_code = self.item_code
				dp_item.item_name = self.item_name
				dp_item.ordered_qty = n_qty
				dp_item.pending_qty = n_qty
				dp_item.qty_to_deliver = n_qty
				dp_item.weight_to_deliver = self.weight_per_unit * n_qty
				dp_item.sales_order = self.sales_order
				dp_item.sorce_warehouse = n_src_warehouse
				dp_item.postal_code = 0
				dp_item.delivery_date = n_date
				dp_item.current_stock = self.current_stock
				dp_item.available_stock = self.available_stock
				dp_item.related_delivey_planning = self.related_delivey_planning
				dp_item.weight_per_unit = self.weight_per_unit
				dp_item.supplier_dc = self.supplier_dc
				dp_item.supplier = n_supplier
				dp_item.save(ignore_permissions=True)
				print("------- per unit ---------- ",self.weight_per_unit,"-------- new Qty ------- ", new_qty)

				n_weight = int(self.weight_per_unit) * new_qty
				frappe.db.set_value('Delivery Planning Item', self.name, {
					'ordered_qty': new_qty,
					'pending_qty': new_qty,
					'qty_to_deliver': new_qty
					# 'weight_to_deliver': new_qty * self.weight_per_unit
				})

			return 1
		else: return 0

	@frappe.whitelist()
	def update_stock(self):	
		docs = frappe.db.get_all(doctype='Bin',
								filters={"warehouse": self.sorce_warehouse,
										"item_code": self.item_code},
								fields= ["projected_qty","actual_qty"])
		print("---------- docs ---------",docs)		
					
		if(docs):
			for doc in docs:
				print("----- doc.actual_qtu", doc.actual_qty)		
				frappe.db.set_value('Delivery Planning Item', self.name, {
						'available_stock' : doc.actual_qty,
						'current_stock' : doc.projected_qty
					})

@frappe.whitelist()
def approve_function(source_names):
	print("------------------------------items",source_names)
	names = list(source_names.split(","))
	print("------------------------------items",names)
	for name in names:
		print("------- 444444444444444 name --------",name)
		x = name.translate({ord(i): None for i in ']"['})
		print(" --- xxxxxxxxxx ------ ",x)
		doc = frappe.get_doc('Delivery Planning Item', x)
		if doc.approved:
			print("Already Approved", x ," status", doc.approved)
			frappe.msgprint(
				msg='Approval status for planning item {item} is already set to {approve}'.format(item = doc.name, approve = doc.approved),
				title='Approval Error',
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
	print("------------------------------items",source_names)
	names = list(source_names.split(","))
	print("------------------------------items",names)
	for name in names:
		print("------- 444444444444444 name --------",name)
		x = name.translate({ord(i): None for i in ']"['})
		print(" --- xxxxxxxxxx ------ ",x)
		doc = frappe.get_doc('Delivery Planning Item', x)
		if doc.approved == "": 
			doc.approved = 'No'
			doc.save()			
			frappe.msgprint(
				msg='Plannig item {item} Rejected'.format(item = doc.name),
				title='Rejection message',
			)
		else:
			print("Already Approved", x ," status", doc.approved)
			frappe.msgprint(
				msg='Approval status for planning item {item} is already set to {approve}'.format(item = doc.name, approve = doc.approved),
				title='Approval Error',
			)
			
	return 1	

# split_function
@frappe.whitelist()
def split_function(source_names):
	print("------------------------------items",source_names)
	names = list(source_names.split(","))
	print("------------------------------items",names)
	for name in names:
		print("------- 444444444444444 name --------",name)
		x = name.translate({ord(i): None for i in ']"['})
		print(" --- xxxxxxxxxx ------ ",x)
		doc = frappe.get_doc('Delivery Planning Item', x)

	return 1
