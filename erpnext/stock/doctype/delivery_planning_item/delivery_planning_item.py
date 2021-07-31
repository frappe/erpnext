# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from bs4.element import Doctype
import frappe
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import update_child_qty_rate

class DeliveryPlanningItem(Document):

	# @frappe.whitelist()
	# def d_status_update(self, dname):
	# 	doc = frappe.get_doc("Delivery Planning Item", 'dname')
	# 	doc.d_status = "Complete"
	# 	doc.save(ignore_permissions=True)

	@frappe.whitelist()
	def split_dp_item(self,n_transporter, n_qty, n_src_warehouse,n_supplier_dc, n_supplier, n_date):
		new_qty = 0
		siname = ""
		sidesc = ""
		sname = ""
		sirate = 0
		newname = ""
		if(n_transporter, n_supplier, n_src_warehouse, n_qty):
			if n_qty != self.ordered_qty:
				new_qty = int(self.ordered_qty) - n_qty
				print("------- per unit ---------- ",self.weight_per_unit,"-------- new Qty ------- ", n_qty)
				n_weight = float(self.weight_per_unit) * n_qty
				print("===== new n weight ===== ", n_weight)
				

				# dp_item.save(ignore_permissions=True)
				print("------- per unit ---------- ",self.weight_per_unit,"-------- new Qty ------- ", new_qty)

				n_weight = float(self.weight_per_unit) * new_qty
				# update old dpi 
				frappe.db.set_value('Delivery Planning Item', self.name, {
					'ordered_qty': new_qty,
					'pending_qty': new_qty,
					'qty_to_deliver': new_qty,
					'weight_to_deliver': float(new_qty) * float(self.weight_per_unit)
				})
			print("----------- values -------------", self.sales_order, self.item_code)
			# soi1 = frappe.get_value( doctype='Sales Order Item', name = self.item_dname,
			# 						fields =['name', 'item_name','item_code',
			# 															'description','rate'],  as_dict=1)	

			soi1 = frappe.db.sql(""" Select name, item_code, item_name, rate, description 
									from `tabSales Order Item` where name = '{0}'
									""".format(self.item_dname),as_dict=1)
			print("----------s01 ============",soi1)															
			
			if soi1:
				for s in soi1:
					sidesc = s.description
					siname = s.item_name 	
					sirate = s.rate	
					sname = s.name	
					sitem_code = s.item_code
							
			print("----------======= name, desc -----=========",sidesc , siname,sname, sirate)
			# soi1.qty = new_qty	
			# soi1.stock_qty = new_qty
			# soi1.amount = sirate * new_qty
			# soi1.save(ignore_permissions=True)
			if (n_transporter):
				frappe.db.set_value('Sales Order', self.sales_order, 'transporter', n_transporter)

			sos = frappe.get_all(doctype = 'Sales Order Item', filters={ 'parent': self.sales_order})
			print("---------------- sos=============",sos, len(sos))
			# sales_order = frappe.get_doc("Sales Order", self.sales_order)
			# print("---------======= sales order ==========------------", sales_order)
			# sales_order.append("items",{
			# 	"item_name" : siname,
			#	"idx" : len(soi1)
			# 	"description" : sidesc,
			# 	"parent" : self.sales_order,
			# 	"parenttype" : "Sales Order",
			# 	"item_code" : self.item_code,
			# 	"delivery_date" : n_date,
			# 	"qty" : n_qty,
			# 	"delivered_by_supplier" : n_supplier_dc,
			# 	"supplier" : n_supplier,
			# 	"uom" : self.uom,
			#	"stock_qty" : n_qty,
			# 	"conversion_factor" : self.conversion_factor
			# })
			# sales_order.save(ignore_permissions=True)


			soi = frappe.new_doc('Sales Order Item')
			soi.stock_qty = n_qty
			soi.idx = len(sos)+1
			soi.rate = sirate
			soi.amount = sirate * n_qty 
			soi.parentfield = "items"
			soi.docstatus = 1
			soi.item_name = siname
			soi.description = sidesc
			soi.parent = self.sales_order
			soi.parenttype = "Sales Order"
			soi.item_code = self.item_code
			soi.delivery_date = n_date	
			soi.qty = n_qty
			soi.delivered_by_supplier = n_supplier_dc
			soi.supplier = n_supplier
			soi.uom = self.uom
			soi.warehouse = n_src_warehouse
			soi.conversion_factor = self.conversion_factor
			print("----------====== new soi ---------========", soi, soi.item_name)
			soi.save(ignore_permissions=True)
			newname = soi.name

			frappe.db.set_value('Sales Order Item', self.item_dname,
								{ 'qty' : new_qty,
								'stock_qty': new_qty,
								'amount' : new_qty * sirate
								})
			
			# trans_items = frappe.get_all("Sales Order Item", filters = {'parent': self.sales_order},
			# 							fields= ['conversion_factor','delivery_date','idx',
			# 							'item_code','name','qty','rate','uom'])
			# print("----------- trans items ===========", trans_items)
			# for t in trans_items:
				
			# 	t['docname'] = t.name
			# 	print("inn  99999999",t)

			# print("updated docname",trans_items)	
			# update_child_qty_rate("Sales Order", str(trans_items), self.sales_order, "items")

			#  Item Name 1,Description 1, UOM Conversion Factor 1,parent, parenttype, idx6280
			# accounts_controller.py 1542 Update update_child_qty_rate
			# utils.js 467 update_child_items 

			# creating new DPI after split
			dp_item = frappe.new_doc("Delivery Planning Item")
			dp_item.item_dname = newname
			dp_item.transporter = n_transporter
			dp_item.customer = self.customer
			dp_item.item_code = self.item_code
			dp_item.item_name = self.item_name
			dp_item.ordered_qty = n_qty
			dp_item.pending_qty = n_qty
			dp_item.qty_to_deliver = n_qty
			dp_item.weight_to_deliver = float(self.weight_per_unit) * n_qty
			dp_item.sales_order = self.sales_order
			dp_item.sorce_warehouse = n_src_warehouse
			dp_item.postal_code = self.postal_code
			dp_item.delivery_date = n_date
			dp_item.current_stock = self.current_stock
			dp_item.available_stock = self.available_stock
			dp_item.related_delivey_planning = self.related_delivey_planning
			dp_item.weight_per_unit = self.weight_per_unit
			dp_item.supplier_dc = n_supplier_dc
			dp_item.supplier = n_supplier
			dp_item.uom = self.uom
			dp_item.conversion_factor = self.conversion_factor
			dp_item.save(ignore_permissions=True)

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
				print("----- doc.actual_qty -----------", doc.actual_qty)	
				frappe.db.sql("""UPDATE `tabDelivery Planning Item` 
					SET current_stock = {0},
					available_stock = {1}
					WHERE name = {2} """.format(doc.projected_qty, doc.actual_qty, "'"+self.name+"'"))	
				# frappe.db.set_value('Delivery Planning Item', self.name, {
				# 		'available_stock' : doc.actual_qty,
				# 		'current_stock' : doc.projected_qty
				# 	})
		# self.save()			

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
				title='Rejection message',
			)
			
	return 1	

# split_function
@frappe.whitelist()
def split_function(source_names, n_transporter, n_qty, n_src_warehouse, n_supplier_dc, n_supplier, n_date):
	print("------------------------------items",source_names)
	dpi = ""
	names = list(source_names.split(","))
	print("------------------------------items",names)
	for name in names:
		print("------- 444444444444444 name --------",name)
		x = name.translate({ord(i): None for i in ']"['})
		print(" --- xxxxxxxxxx ------ ",x)
		doc = frappe.get_doc('Delivery Planning Item', x)
		print(" --- xxxxx    doc        xxxxx ------ ",doc, doc.item_code)

	print("------------- print -------",source_names, n_transporter, n_qty, n_src_warehouse, n_supplier_dc, n_supplier, n_date)
	
	new_qty = 0
	siname = ""
	sidesc = ""
	sname = ""
	sirate = 0
	newname = ""
	if(n_transporter, n_supplier, n_src_warehouse, n_qty):
		if n_qty != doc.ordered_qty:
			new_qty = float(doc.ordered_qty) - float(n_qty)
			print("------- per unit ---------- ",doc.weight_per_unit,"-------- new Qty ------- ", n_qty)
			n_weight = float(doc.weight_per_unit) * float(n_qty)
			print("===== new n weight ===== ", n_weight)
			

			# dp_item.save(ignore_permissions=True)
			print("------- per unit ---------- ",doc.weight_per_unit,"-------- new Qty ------- ", new_qty)

			n_weight = float(doc.weight_per_unit) * new_qty
			# update old dpi 
			frappe.db.set_value('Delivery Planning Item', doc.name, {
				'ordered_qty': new_qty,
				'pending_qty': new_qty,
				'qty_to_deliver': new_qty,
				'weight_to_deliver': float(new_qty) * float(doc.weight_per_unit)
			})
		print("----------- values -------------", doc.sales_order, doc.item_code)
		dp_item = frappe.new_doc("Delivery Planning Item")
		# dp_item.item_dname = newname
		dp_item.transporter = n_transporter
		dp_item.customer = doc.customer
		dp_item.item_code = doc.item_code
		dp_item.item_name = doc.item_name
		dp_item.ordered_qty = n_qty
		dp_item.pending_qty = n_qty
		dp_item.qty_to_deliver = n_qty
		dp_item.weight_to_deliver = float(doc.weight_per_unit) * float(n_qty)
		dp_item.sales_order = doc.sales_order
		dp_item.sorce_warehouse = n_src_warehouse
		dp_item.postal_code = doc.postal_code
		dp_item.delivery_date = n_date
		dp_item.current_stock = doc.current_stock
		dp_item.available_stock = doc.available_stock
		dp_item.related_delivey_planning = doc.related_delivey_planning
		dp_item.weight_per_unit = doc.weight_per_unit
		dp_item.supplier_dc = n_supplier_dc
		dp_item.supplier = n_supplier
		dp_item.uom = doc.uom
		dp_item.conversion_factor = doc.conversion_factor
		dp_item.is_split = 1
		dp_item.split_from_item = doc.name
		dp_item.save(ignore_permissions=True)

	return 1
