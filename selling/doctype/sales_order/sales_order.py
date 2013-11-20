# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
import webnotes.utils

from webnotes.utils import cstr, flt, getdate
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint
from webnotes.model.mapper import get_mapped_doclist

from controllers.selling_controller import SellingController

class DocType(SellingController):
	def __init__(self, doc, doclist=None):
		self.doc = doc
		if not doclist: doclist = []
		self.doclist = doclist
		self.tname = 'Sales Order Item'
		self.fname = 'sales_order_details'
		self.person_tname = 'Target Detail'
		self.partner_tname = 'Partner Target Detail'
		self.territory_tname = 'Territory Target Detail'
	
	def validate_mandatory(self):
		# validate transaction date v/s delivery date
		if self.doc.delivery_date:
			if getdate(self.doc.transaction_date) > getdate(self.doc.delivery_date):
				msgprint("Expected Delivery Date cannot be before Sales Order Date")
				raise Exception
	
	def validate_po(self):
		# validate p.o date v/s delivery date
		if self.doc.po_date and self.doc.delivery_date and getdate(self.doc.po_date) > getdate(self.doc.delivery_date):
			msgprint("Expected Delivery Date cannot be before Purchase Order Date")
			raise Exception	
		
		if self.doc.po_no and self.doc.customer:
			so = webnotes.conn.sql("select name from `tabSales Order` \
				where ifnull(po_no, '') = %s and name != %s and docstatus < 2\
				and customer = %s", (self.doc.po_no, self.doc.name, self.doc.customer))
			if so and so[0][0]:
				msgprint("""Another Sales Order (%s) exists against same PO No and Customer. 
					Please be sure, you are not making duplicate entry.""" % so[0][0])
	
	def validate_for_items(self):
		check_list, flag = [], 0
		chk_dupl_itm = []
		for d in getlist(self.doclist, 'sales_order_details'):
			e = [d.item_code, d.description, d.reserved_warehouse, d.prevdoc_docname or '']
			f = [d.item_code, d.description]

			if webnotes.conn.get_value("Item", d.item_code, "is_stock_item") == 'Yes':
				if not d.reserved_warehouse:
					msgprint("""Please enter Reserved Warehouse for item %s 
						as it is stock Item""" % d.item_code, raise_exception=1)
				
				if e in check_list:
					msgprint("Item %s has been entered twice." % d.item_code)
				else:
					check_list.append(e)
			else:
				if f in chk_dupl_itm:
					msgprint("Item %s has been entered twice." % d.item_code)
				else:
					chk_dupl_itm.append(f)

			# used for production plan
			d.transaction_date = self.doc.transaction_date
			
			tot_avail_qty = webnotes.conn.sql("select projected_qty from `tabBin` \
				where item_code = '%s' and warehouse = '%s'" % (d.item_code,d.reserved_warehouse))
			d.projected_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0

	def validate_sales_mntc_quotation(self):
		for d in getlist(self.doclist, 'sales_order_details'):
			if d.prevdoc_docname:
				res = webnotes.conn.sql("select name from `tabQuotation` where name=%s and order_type = %s", (d.prevdoc_docname, self.doc.order_type))
				if not res:
					msgprint("""Order Type (%s) should be same in Quotation: %s \
						and current Sales Order""" % (self.doc.order_type, d.prevdoc_docname))

	def validate_order_type(self):
		super(DocType, self).validate_order_type()
		
	def validate_delivery_date(self):
		if self.doc.order_type == 'Sales' and not self.doc.delivery_date:
			msgprint("Please enter 'Expected Delivery Date'")
			raise Exception
		
		self.validate_sales_mntc_quotation()

	def validate_proj_cust(self):
		if self.doc.project_name and self.doc.customer_name:
			res = webnotes.conn.sql("select name from `tabProject` where name = '%s' and (customer = '%s' or ifnull(customer,'')='')"%(self.doc.project_name, self.doc.customer))
			if not res:
				msgprint("Customer - %s does not belong to project - %s. \n\nIf you want to use project for multiple customers then please make customer details blank in project - %s."%(self.doc.customer,self.doc.project_name,self.doc.project_name))
				raise Exception
	
	def validate(self):
		super(DocType, self).validate()
		
		self.validate_order_type()
		self.validate_delivery_date()
		self.validate_mandatory()
		self.validate_proj_cust()
		self.validate_po()
		self.validate_uom_is_integer("stock_uom", "qty")
		self.validate_for_items()
		self.validate_warehouse()

		from stock.doctype.packed_item.packed_item import make_packing_list
		self.doclist = make_packing_list(self,'sales_order_details')

		self.validate_with_previous_doc()
				
		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Stopped", 
			"Cancelled"])

		if not self.doc.billing_status: self.doc.billing_status = 'Not Billed'
		if not self.doc.delivery_status: self.doc.delivery_status = 'Not Delivered'
		
		
	def validate_warehouse(self):
		from stock.utils import validate_warehouse_user, validate_warehouse_company
		
		warehouses = list(set([d.reserved_warehouse for d in 
			self.doclist.get({"doctype": self.tname}) if d.reserved_warehouse]))
				
		for w in warehouses:
			validate_warehouse_user(w)
			validate_warehouse_company(w, self.doc.company)
		
	def validate_with_previous_doc(self):
		super(DocType, self).validate_with_previous_doc(self.tname, {
			"Quotation": {
				"ref_dn_field": "prevdoc_docname",
				"compare_fields": [["company", "="], ["currency", "="]]
			}
		})

		
	def update_enquiry_status(self, prevdoc, flag):
		enq = webnotes.conn.sql("select t2.prevdoc_docname from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.name=%s", prevdoc)
		if enq:
			webnotes.conn.sql("update `tabOpportunity` set status = %s where name=%s",(flag,enq[0][0]))

	def update_prevdoc_status(self, flag):				
		for quotation in self.doclist.get_distinct_values("prevdoc_docname"):
			bean = webnotes.bean("Quotation", quotation)
			if bean.doc.docstatus==2:
				webnotes.throw(quotation + ": " + webnotes._("Quotation is cancelled."))
				
			bean.get_controller().set_status(update=True)

	def on_submit(self):
		self.update_stock_ledger(update_stock = 1)

		self.check_credit(self.doc.grand_total)
		
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.grand_total, self)
		
		self.update_prevdoc_status('submit')
		webnotes.conn.set(self.doc, 'status', 'Submitted')
	
	def on_cancel(self):
		# Cannot cancel stopped SO
		if self.doc.status == 'Stopped':
			msgprint("Sales Order : '%s' cannot be cancelled as it is Stopped. Unstop it for any further transactions" %(self.doc.name))
			raise Exception
		self.check_nextdoc_docstatus()
		self.update_stock_ledger(update_stock = -1)
		
		self.update_prevdoc_status('cancel')
		
		webnotes.conn.set(self.doc, 'status', 'Cancelled')
		
	def check_nextdoc_docstatus(self):
		# Checks Delivery Note
		submit_dn = webnotes.conn.sql("select t1.name from `tabDelivery Note` t1,`tabDelivery Note Item` t2 where t1.name = t2.parent and t2.against_sales_order = %s and t1.docstatus = 1", self.doc.name)
		if submit_dn:
			msgprint("Delivery Note : " + cstr(submit_dn[0][0]) + " has been submitted against " + cstr(self.doc.doctype) + ". Please cancel Delivery Note : " + cstr(submit_dn[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
			
		# Checks Sales Invoice
		submit_rv = webnotes.conn.sql("select t1.name from `tabSales Invoice` t1,`tabSales Invoice Item` t2 where t1.name = t2.parent and t2.sales_order = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_rv:
			msgprint("Sales Invoice : " + cstr(submit_rv[0][0]) + " has already been submitted against " +cstr(self.doc.doctype)+ ". Please cancel Sales Invoice : "+ cstr(submit_rv[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
			
		#check maintenance schedule
		submit_ms = webnotes.conn.sql("select t1.name from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2 where t2.parent=t1.name and t2.prevdoc_docname = %s and t1.docstatus = 1",self.doc.name)
		if submit_ms:
			msgprint("Maintenance Schedule : " + cstr(submit_ms[0][0]) + " has already been submitted against " +cstr(self.doc.doctype)+ ". Please cancel Maintenance Schedule : "+ cstr(submit_ms[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
			
		# check maintenance visit
		submit_mv = webnotes.conn.sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent=t1.name and t2.prevdoc_docname = %s and t1.docstatus = 1",self.doc.name)
		if submit_mv:
			msgprint("Maintenance Visit : " + cstr(submit_mv[0][0]) + " has already been submitted against " +cstr(self.doc.doctype)+ ". Please cancel Maintenance Visit : " + cstr(submit_mv[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
		
		# check production order
		pro_order = webnotes.conn.sql("""select name from `tabProduction Order` where sales_order = %s and docstatus = 1""", self.doc.name)
		if pro_order:
			msgprint("""Production Order: %s exists against this sales order. 
				Please cancel production order first and then cancel this sales order""" % 
				pro_order[0][0], raise_exception=1)

	def check_modified_date(self):
		mod_db = webnotes.conn.sql("select modified from `tabSales Order` where name = '%s'" % self.doc.name)
		date_diff = webnotes.conn.sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.doc.modified)))
		if date_diff and date_diff[0][0]:
			msgprint("%s: %s has been modified after you have opened. Please Refresh"
				% (self.doc.doctype, self.doc.name), raise_exception=1)

	def stop_sales_order(self):
		self.check_modified_date()
		self.update_stock_ledger(-1)
		webnotes.conn.set(self.doc, 'status', 'Stopped')
		msgprint("""%s: %s has been Stopped. To make transactions against this Sales Order 
			you need to Unstop it.""" % (self.doc.doctype, self.doc.name))

	def unstop_sales_order(self):
		self.check_modified_date()
		self.update_stock_ledger(1)
		webnotes.conn.set(self.doc, 'status', 'Submitted')
		msgprint("%s: %s has been Unstopped" % (self.doc.doctype, self.doc.name))


	def update_stock_ledger(self, update_stock):
		from stock.utils import update_bin
		for d in self.get_item_list():
			if webnotes.conn.get_value("Item", d['item_code'], "is_stock_item") == "Yes":
				args = {
					"item_code": d['item_code'],
					"warehouse": d['reserved_warehouse'], 
					"reserved_qty": flt(update_stock) * flt(d['reserved_qty']),
					"posting_date": self.doc.transaction_date,
					"voucher_type": self.doc.doctype,
					"voucher_no": self.doc.name,
					"is_amended": self.doc.amended_from and 'Yes' or 'No'
				}
				update_bin(args)

	def on_update(self):
		pass
		
	def get_portal_page(self):
		return "order" if self.doc.docstatus==1 else None
		
def set_missing_values(source, target):
	bean = webnotes.bean(target)
	bean.run_method("onload_post_render")
	
@webnotes.whitelist()
def make_material_request(source_name, target_doclist=None):	
	def postprocess(source, doclist):
		doclist[0].material_request_type = "Purchase"
	
	doclist = get_mapped_doclist("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Material Request", 
			"validation": {
				"docstatus": ["=", 1]
			}
		}, 
		"Sales Order Item": {
			"doctype": "Material Request Item", 
			"field_map": {
				"parent": "sales_order_no", 
				"reserved_warehouse": "warehouse", 
				"stock_uom": "uom"
			}
		}
	}, target_doclist, postprocess)
	
	return [(d if isinstance(d, dict) else d.fields) for d in doclist]

@webnotes.whitelist()
def make_delivery_note(source_name, target_doclist=None):	
	def update_item(obj, target, source_parent):
		target.amount = (flt(obj.qty) - flt(obj.delivered_qty)) * flt(obj.basic_rate)
		target.export_amount = (flt(obj.qty) - flt(obj.delivered_qty)) * flt(obj.export_rate)
		target.qty = flt(obj.qty) - flt(obj.delivered_qty)
			
	doclist = get_mapped_doclist("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Delivery Note", 
			"field_map": {
				"shipping_address": "address_display", 
				"shipping_address_name": "customer_address", 
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		}, 
		"Sales Order Item": {
			"doctype": "Delivery Note Item", 
			"field_map": {
				"export_rate": "export_rate", 
				"name": "prevdoc_detail_docname", 
				"parent": "against_sales_order", 
				"reserved_warehouse": "warehouse"
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.delivered_qty < doc.qty
		}, 
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges", 
			"add_if_empty": True
		}, 
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}, target_doclist, set_missing_values)
	
	return [d.fields for d in doclist]

@webnotes.whitelist()
def make_sales_invoice(source_name, target_doclist=None):
	def set_missing_values(source, target):
		bean = webnotes.bean(target)
		bean.doc.is_pos = 0
		bean.run_method("onload_post_render")
		
	def update_item(obj, target, source_parent):
		target.export_amount = flt(obj.export_amount) - flt(obj.billed_amt)
		target.amount = target.export_amount * flt(source_parent.conversion_rate)
		target.qty = obj.export_rate and target.export_amount / flt(obj.export_rate) or obj.qty
			
	doclist = get_mapped_doclist("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Sales Invoice", 
			"validation": {
				"docstatus": ["=", 1]
			}
		}, 
		"Sales Order Item": {
			"doctype": "Sales Invoice Item", 
			"field_map": {
				"name": "so_detail", 
				"parent": "sales_order", 
				"reserved_warehouse": "warehouse"
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.amount==0 or doc.billed_amt < doc.export_amount
		}, 
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges", 
			"add_if_empty": True
		}, 
		"Sales Team": {
			"doctype": "Sales Team", 
			"add_if_empty": True
		}
	}, target_doclist, set_missing_values)
	
	return [d.fields for d in doclist]
	
@webnotes.whitelist()
def make_maintenance_schedule(source_name, target_doclist=None):
	maint_schedule = webnotes.conn.sql("""select t1.name 
		from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2 
		where t2.parent=t1.name and t2.prevdoc_docname=%s and t1.docstatus=1""", source_name)
		
	if not maint_schedule:
		doclist = get_mapped_doclist("Sales Order", source_name, {
			"Sales Order": {
				"doctype": "Maintenance Schedule", 
				"field_map": {
					"name": "sales_order_no"
				}, 
				"validation": {
					"docstatus": ["=", 1]
				}
			}, 
			"Sales Order Item": {
				"doctype": "Maintenance Schedule Item", 
				"field_map": {
					"parent": "prevdoc_docname"
				},
				"add_if_empty": True
			}
		}, target_doclist)
	
		return [d.fields for d in doclist]
	
@webnotes.whitelist()
def make_maintenance_visit(source_name, target_doclist=None):
	visit = webnotes.conn.sql("""select t1.name 
		from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 
		where t2.parent=t1.name and t2.prevdoc_docname=%s 
		and t1.docstatus=1 and t1.completion_status='Fully Completed'""", source_name)
		
	if not visit:
		doclist = get_mapped_doclist("Sales Order", source_name, {
			"Sales Order": {
				"doctype": "Maintenance Visit", 
				"field_map": {
					"name": "sales_order_no"
				},
				"validation": {
					"docstatus": ["=", 1]
				}
			}, 
			"Sales Order Item": {
				"doctype": "Maintenance Visit Purpose", 
				"field_map": {
					"parent": "prevdoc_docname", 
					"parenttype": "prevdoc_doctype"
				},
				"add_if_empty": True
			}
		}, target_doclist)
	
		return [d.fields for d in doclist]
