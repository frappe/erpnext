# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt
from webnotes.model.utils import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, _

from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.tname = 'Material Request Item'
		self.fname = 'indent_details'

	def check_if_already_pulled(self):
		pass#if self.[d.sales_order_no for d in getlist(self.doclist, 'indent_details')]

	def validate_qty_against_so(self):
		so_items = {} # Format --> {'SO/00001': {'Item/001': 120, 'Item/002': 24}}
		for d in getlist(self.doclist, 'indent_details'):
			if d.sales_order_no:
				if not so_items.has_key(d.sales_order_no):
					so_items[d.sales_order_no] = {d.item_code: flt(d.qty)}
				else:
					if not so_items[d.sales_order_no].has_key(d.item_code):
						so_items[d.sales_order_no][d.item_code] = flt(d.qty)
					else:
						so_items[d.sales_order_no][d.item_code] += flt(d.qty)
		
		for so_no in so_items.keys():
			for item in so_items[so_no].keys():
				already_indented = webnotes.conn.sql("select sum(qty) from `tabMaterial Request Item` where item_code = '%s' and sales_order_no = '%s' and docstatus = 1 and parent != '%s'" % (item, so_no, self.doc.name))
				already_indented = already_indented and flt(already_indented[0][0]) or 0
				
				actual_so_qty = webnotes.conn.sql("select sum(qty) from `tabSales Order Item` where parent = '%s' and item_code = '%s' and docstatus = 1 group by parent" % (so_no, item))
				actual_so_qty = actual_so_qty and flt(actual_so_qty[0][0]) or 0

				if flt(so_items[so_no][item]) + already_indented > actual_so_qty:
					msgprint("You can raise indent of maximum qty: %s for item: %s against sales order: %s\n Anyway, you can add more qty in new row for the same item." % (actual_so_qty - already_indented, item, so_no), raise_exception=1)
				
	def validate_schedule_date(self):
		for d in getlist(self.doclist, 'indent_details'):
			if d.schedule_date < self.doc.transaction_date:
				msgprint("Expected Date cannot be before Material Request Date")
				raise Exception
				
	# Validate
	# ---------------------
	def validate(self):
		super(DocType, self).validate()
		
		self.validate_schedule_date()
		self.validate_uom_is_integer("uom", "qty")
		
		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Stopped", "Cancelled"])
		
		self.validate_value("material_request_type", "in", ["Purchase", "Transfer"])

		pc_obj = get_obj(dt='Purchase Common')
		pc_obj.validate_for_items(self)

		self.validate_qty_against_so()
	
	def update_bin(self, is_submit, is_stopped):
		""" Update Quantity Requested for Purchase in Bin for Material Request of type 'Purchase'"""
		
		from stock.utils import update_bin
		for d in getlist(self.doclist, 'indent_details'):
			if webnotes.conn.get_value("Item", d.item_code, "is_stock_item") == "Yes":
				if not d.warehouse:
					msgprint("Please Enter Warehouse for Item %s as it is stock item" 
						% cstr(d.item_code), raise_exception=1)
					
				qty =flt(d.qty)
				if is_stopped:
					qty = (d.qty > d.ordered_qty) and flt(flt(d.qty) - flt(d.ordered_qty)) or 0
			
				args = {
					"item_code": d.item_code,
					"warehouse": d.warehouse,
					"indented_qty": (is_submit and 1 or -1) * flt(qty),
					"posting_date": self.doc.transaction_date
				}
				update_bin(args)		
		
	def on_submit(self):
		webnotes.conn.set(self.doc,'status','Submitted')
		self.update_bin(is_submit = 1, is_stopped = 0)
	
	def check_modified_date(self):
		mod_db = webnotes.conn.sql("select modified from `tabMaterial Request` where name = '%s'" % self.doc.name)
		date_diff = webnotes.conn.sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.doc.modified)))
		
		if date_diff and date_diff[0][0]:
			msgprint(cstr(self.doc.doctype) +" => "+ cstr(self.doc.name) +" has been modified. Please Refresh. ")
			raise Exception

	def update_status(self, status):
		self.check_modified_date()
		# Step 1:=> Update Bin
		self.update_bin(is_submit = (status == 'Submitted') and 1 or 0, is_stopped = 1)

		# Step 2:=> Set status 
		webnotes.conn.set(self.doc,'status',cstr(status))
		
		# Step 3:=> Acknowledge User
		msgprint(self.doc.doctype + ": " + self.doc.name + " has been %s." % ((status == 'Submitted') and 'Unstopped' or cstr(status)) )
 

	def on_cancel(self):
		# Step 1:=> Get Purchase Common Obj
		pc_obj = get_obj(dt='Purchase Common')
		
		# Step 2:=> Check for stopped status
		pc_obj.check_for_stopped_status(self.doc.doctype, self.doc.name)
		
		# Step 3:=> Check if Purchase Order has been submitted against current Material Request
		pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Order', docname = self.doc.name, detail_doctype = 'Purchase Order Item')
		# Step 4:=> Update Bin
		self.update_bin(is_submit = 0, is_stopped = (cstr(self.doc.status) == 'Stopped') and 1 or 0)
		
		# Step 5:=> Set Status
		webnotes.conn.set(self.doc,'status','Cancelled')
		
	def update_completed_qty(self, mr_items=None):
		if self.doc.material_request_type != "Transfer":
			return
			
		item_doclist = self.doclist.get({"parentfield": "indent_details"})
		
		if not mr_items:
			mr_items = [d.name for d in item_doclist]
		
		per_ordered = 0.0
		for d in item_doclist:
			if d.name in mr_items:
				d.ordered_qty =  flt(webnotes.conn.sql("""select sum(transfer_qty) 
					from `tabStock Entry Detail` where material_request = %s 
					and material_request_item = %s and docstatus = 1""", 
					(self.doc.name, d.name))[0][0])
				webnotes.conn.set_value(d.doctype, d.name, "ordered_qty", d.ordered_qty)
				
			# note: if qty is 0, its row is still counted in len(item_doclist)
			# hence adding 1 to per_ordered
			if (d.ordered_qty > d.qty) or not d.qty:
				per_ordered += 1.0
			elif d.qty > 0:
				per_ordered += flt(d.ordered_qty / flt(d.qty))
		
		self.doc.per_ordered = flt((per_ordered / flt(len(item_doclist))) * 100.0, 2)
		webnotes.conn.set_value(self.doc.doctype, self.doc.name, "per_ordered", self.doc.per_ordered)
		
def update_completed_qty(controller, caller_method):
	if controller.doc.doctype == "Stock Entry":
		material_request_map = {}
		
		for d in controller.doclist.get({"parentfield": "mtn_details"}):
			if d.material_request:
				if d.material_request not in material_request_map:
					material_request_map[d.material_request] = []
				material_request_map[d.material_request].append(d.material_request_item)
			
		for mr_name, mr_items in material_request_map.items():
			mr_obj = webnotes.get_obj("Material Request", mr_name, with_children=1)
			mr_doctype = webnotes.get_doctype("Material Request")
			
			if mr_obj.doc.status in ["Stopped", "Cancelled"]:
				msgprint(_("Material Request") + ": %s, " % mr_obj.doc.name 
					+ _(mr_doctype.get_label("status")) + " = %s. " % _(mr_obj.doc.status)
					+ _("Cannot continue."), raise_exception=webnotes.InvalidStatusError)
				
			_update_requested_qty(controller, mr_obj, mr_items)
			
			# update ordered percentage and qty
			mr_obj.update_completed_qty(mr_items)
			
def _update_requested_qty(controller, mr_obj, mr_items):
	"""update requested qty (before ordered_qty is updated)"""
	from stock.utils import update_bin
	for mr_item_name in mr_items:
		mr_item = mr_obj.doclist.getone({"parentfield": "indent_details", "name": mr_item_name})
		se_detail = controller.doclist.getone({"parentfield": "mtn_details",
			"material_request": mr_obj.doc.name, "material_request_item": mr_item_name})
	
		mr_item.ordered_qty = flt(mr_item.ordered_qty)
		mr_item.qty = flt(mr_item.qty)
		se_detail.transfer_qty = flt(se_detail.transfer_qty)
	
		if se_detail.docstatus == 2 and mr_item.ordered_qty > mr_item.qty \
				and se_detail.transfer_qty == mr_item.ordered_qty:
			add_indented_qty = mr_item.qty
		elif se_detail.docstatus == 1 and \
				mr_item.ordered_qty + se_detail.transfer_qty > mr_item.qty:
			add_indented_qty = mr_item.qty - mr_item.ordered_qty
		else:
			add_indented_qty = se_detail.transfer_qty
	
		update_bin({
			"item_code": se_detail.item_code,
			"warehouse": se_detail.t_warehouse,
			"indented_qty": (se_detail.docstatus==2 and 1 or -1) * add_indented_qty,
			"posting_date": controller.doc.posting_date,
		})

def set_missing_values(source, target_doclist):
	po = webnotes.bean(target_doclist)
	po.run_method("set_missing_values")
	
def update_item(obj, target, source_parent):
	target.conversion_factor = 1
	target.qty = flt(obj.qty) - flt(obj.ordered_qty)

@webnotes.whitelist()
def make_purchase_order(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist

	doclist = get_mapped_doclist("Material Request", source_name, 	{
		"Material Request": {
			"doctype": "Purchase Order", 
			"validation": {
				"docstatus": ["=", 1],
				"material_request_type": ["=", "Purchase"]
			}
		}, 
		"Material Request Item": {
			"doctype": "Purchase Order Item", 
			"field_map": [
				["name", "prevdoc_detail_docname"], 
				["parent", "prevdoc_docname"], 
				["parenttype", "prevdoc_doctype"], 
				["uom", "stock_uom"],
				["uom", "uom"]
			],
			"postprocess": update_item
		}
	}, target_doclist, set_missing_values)

	return [d.fields for d in doclist]
	
@webnotes.whitelist()
def make_purchase_order_based_on_supplier(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
	if target_doclist:
		if isinstance(target_doclist, basestring):
			import json
			target_doclist = webnotes.doclist(json.loads(target_doclist))
		target_doclist = target_doclist.get({"parentfield": ["!=", "po_details"]})
		
	material_requests, supplier_items = get_material_requests_based_on_supplier(source_name)
	
	def postprocess(source, target_doclist):
		target_doclist[0].supplier = source_name
		set_missing_values(source, target_doclist)
		
		po_items = target_doclist.get({"parentfield": "po_details"})
		target_doclist = target_doclist.get({"parentfield": ["!=", "po_details"]}) + \
			[d for d in po_items 
				if d.fields.get("item_code") in supplier_items and d.fields.get("qty") > 0]
		
		return target_doclist
		
	for mr in material_requests:
		target_doclist = get_mapped_doclist("Material Request", mr, 	{
			"Material Request": {
				"doctype": "Purchase Order", 
			}, 
			"Material Request Item": {
				"doctype": "Purchase Order Item", 
				"field_map": [
					["name", "prevdoc_detail_docname"], 
					["parent", "prevdoc_docname"], 
					["parenttype", "prevdoc_doctype"], 
					["uom", "stock_uom"],
					["uom", "uom"]
				],
				"postprocess": update_item
			}
		}, target_doclist, postprocess)
	
	return [d.fields for d in target_doclist]
	
def get_material_requests_based_on_supplier(supplier):
	supplier_items = [d[0] for d in webnotes.conn.get_values("Item", 
		{"default_supplier": supplier})]
	material_requests = webnotes.conn.sql_list("""select distinct mr.name 
		from `tabMaterial Request` mr, `tabMaterial Request Item` mr_item
		where mr.name = mr_item.parent
		and mr_item.item_code in (%s)
		and mr.material_request_type = 'Purchase'
		and ifnull(mr.per_ordered, 0) < 99.99
		and mr.docstatus = 1
		and mr.status != 'Stopped'""" % ', '.join(['%s']*len(supplier_items)),
		tuple(supplier_items))
	return material_requests, supplier_items
	
@webnotes.whitelist()
def make_supplier_quotation(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist

	doclist = get_mapped_doclist("Material Request", source_name, {
		"Material Request": {
			"doctype": "Supplier Quotation", 
			"validation": {
				"docstatus": ["=", 1],
				"material_request_type": ["=", "Purchase"]
			}
		}, 
		"Material Request Item": {
			"doctype": "Supplier Quotation Item", 
			"field_map": {
				"name": "prevdoc_detail_docname", 
				"parent": "prevdoc_docname", 
				"parenttype": "prevdoc_doctype"
			}
		}
	}, target_doclist, set_missing_values)

	return [d.fields for d in doclist]
	
@webnotes.whitelist()
def make_stock_entry(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
	
	def update_item(obj, target, source_parent):
		target.conversion_factor = 1
		target.qty = flt(obj.qty) - flt(obj.ordered_qty)
		target.transfer_qty = flt(obj.qty) - flt(obj.ordered_qty)
	
	def set_missing_values(source, target):
		target[0].purpose = "Material Transfer"
		se = webnotes.bean(target)
		se.run_method("get_stock_and_rate")

	doclist = get_mapped_doclist("Material Request", source_name, {
		"Material Request": {
			"doctype": "Stock Entry", 
			"validation": {
				"docstatus": ["=", 1],
				"material_request_type": ["=", "Transfer"]
			}
		}, 
		"Material Request Item": {
			"doctype": "Stock Entry Detail", 
			"field_map": {
				"name": "material_request_item", 
				"parent": "material_request", 
				"uom": "stock_uom", 
				"warehouse": "t_warehouse"
			},
			"postprocess": update_item
		}
	}, target_doclist, set_missing_values)

	return [d.fields for d in doclist]