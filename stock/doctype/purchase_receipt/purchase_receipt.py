# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt, cint
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes.model.doc import Document
from webnotes import msgprint, _

sql = webnotes.conn.sql

from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.tname = 'Purchase Receipt Item'
		self.fname = 'purchase_receipt_details'
		self.count = 0

	def validate_fiscal_year(self):
		get_obj(dt = 'Purchase Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.posting_date,'Transaction Date')

	# GET TERMS & CONDITIONS
	# =====================================================================================
	def get_tc_details(self):
		return get_obj('Purchase Common').get_tc_details(self)


	# get available qty at warehouse
	def get_bin_details(self, arg = ''):
		return get_obj(dt='Purchase Common').get_bin_details(arg)

	# Pull Purchase Order
	def get_po_details(self):
		self.validate_prev_docname()
		get_obj('DocType Mapper', 'Purchase Order-Purchase Receipt').dt_map('Purchase Order', 'Purchase Receipt', self.doc.purchase_order_no, self.doc, self.doclist, "[['Purchase Order','Purchase Receipt'],['Purchase Order Item', 'Purchase Receipt Item'],['Purchase Taxes and Charges','Purchase Taxes and Charges']]")

	# validate if PO has been pulled twice
	def validate_prev_docname(self):
		for d in getlist(self.doclist, 'purchase_receipt_details'):
			if self.doc.purchase_order_no and d.prevdoc_docname and self.doc.purchase_order_no == d.prevdoc_docname:
				msgprint(cstr(self.doc.purchase_order_no) + " Purchase Order details have already been pulled. ")
				raise Exception


	# validation
	#-------------------------------------------------------------------------------------------------------------
	# validate accepted and rejected qty
	def validate_accepted_rejected_qty(self):
		for d in getlist(self.doclist, "purchase_receipt_details"):

			# If Reject Qty than Rejected warehouse is mandatory
			if flt(d.rejected_qty) and (not self.doc.rejected_warehouse):
				msgprint("Rejected Warehouse is necessary if there are rejections.")
				raise Exception

			# Check Received Qty = Accepted Qty + Rejected Qty
			if ((flt(d.qty) + flt(d.rejected_qty)) != flt(d.received_qty)):

				msgprint("Sum of Accepted Qty and Rejected Qty must be equal to Received quantity. Error for Item: " + cstr(d.item_code))
				raise Exception


	def validate_challan_no(self):
		"Validate if same challan no exists for same supplier in a submitted purchase receipt"
		if self.doc.challan_no:
			exists = webnotes.conn.sql("""
			SELECT name FROM `tabPurchase Receipt`
			WHERE name!=%s AND supplier=%s AND challan_no=%s
		AND docstatus=1""", (self.doc.name, self.doc.supplier, self.doc.challan_no))
			if exists:
				webnotes.msgprint("Another Purchase Receipt using the same Challan No. already exists.\
			Please enter a valid Challan No.", raise_exception=1)

	def update_valuation_rate(self):
		for d in self.doclist.get({"parentfield": "purchase_receipt_details"}):
			if d.qty:
				d.valuation_rate = (flt(d.purchase_rate) + flt(d.item_tax_amount)/flt(d.qty)
					+ flt(d.rm_supp_cost) / flt(d.qty)) / flt(d.conversion_factor)
			else:
				d.valuation_rate = 0.0

	def po_required(self):
		res = sql("select value from `tabSingles` where doctype = 'Global Defaults' and field = 'po_required'")
		if res and res[0][0]== 'Yes':
			 for d in getlist(self.doclist,'purchase_receipt_details'):
				 if not d.prevdoc_docname:
					 msgprint("Purchse Order No. required against item %s"%d.item_code)
					 raise Exception

	def validate(self):
		super(DocType, self).validate()
		
		self.po_required()
		self.validate_fiscal_year()

		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Cancelled"])

		self.validate_accepted_rejected_qty()
		self.validate_inspection()						 # Validate Inspection
		get_obj('Stock Ledger').validate_serial_no(self, 'purchase_receipt_details')
		self.validate_challan_no()

		pc_obj = get_obj(dt='Purchase Common')
		pc_obj.validate_for_items(self)
		pc_obj.get_prevdoc_date(self)
		pc_obj.validate_reference_value(self)
		self.check_for_stopped_status(pc_obj)

		# update valuation rate
		self.update_valuation_rate()
		# sub-contracting
		self.validate_for_subcontracting()
		self.update_raw_materials_supplied()

	def on_update(self):
		if self.doc.rejected_warehouse:
			for d in getlist(self.doclist,'purchase_receipt_details'):
				d.rejected_warehouse = self.doc.rejected_warehouse

		get_obj('Stock Ledger').scrub_serial_nos(self)
		self.scrub_rejected_serial_nos()


	def scrub_rejected_serial_nos(self):
		for d in getlist(self.doclist, 'purchase_receipt_details'):
			if d.rejected_serial_no:
				d.rejected_serial_no = cstr(d.rejected_serial_no).strip().replace(',', '\n')
				d.save()

	def update_stock(self, is_submit):
		pc_obj = get_obj('Purchase Common')
		self.values = []
		for d in getlist(self.doclist, 'purchase_receipt_details'):
			if webnotes.conn.get_value("Item", d.item_code, "is_stock_item") == "Yes":
				ord_qty = 0
				pr_qty = flt(d.qty) * flt(d.conversion_factor)

				if cstr(d.prevdoc_doctype) == 'Purchase Order':
					# get qty and pending_qty of prevdoc
					curr_ref_qty = pc_obj.get_qty( d.doctype, 'prevdoc_detail_docname',
					 	d.prevdoc_detail_docname, 'Purchase Order Item', 
						'Purchase Order - Purchase Receipt', self.doc.name)
					max_qty, qty, curr_qty = flt(curr_ref_qty.split('~~~')[1]), \
					 	flt(curr_ref_qty.split('~~~')[0]), 0

					if flt(qty) + flt(pr_qty) > flt(max_qty):
						curr_qty = (flt(max_qty) - flt(qty)) * flt(d.conversion_factor)
					else:
						curr_qty = flt(pr_qty)

					ord_qty = -flt(curr_qty)
					
					# update ordered qty in bin
					args = {
						"item_code": d.item_code,
						"posting_date": self.doc.posting_date,
						"ordered_qty": (is_submit and 1 or -1) * flt(ord_qty)
					}
					get_obj("Warehouse", d.warehouse).update_bin(args)

				# UPDATE actual qty to warehouse by pr_qty
				if pr_qty:
					self.make_sl_entry(d, d.warehouse, flt(pr_qty), d.valuation_rate, is_submit)
				
				# UPDATE actual to rejected warehouse by rejected qty
				if flt(d.rejected_qty) > 0:
					self.make_sl_entry(d, self.doc.rejected_warehouse, flt(d.rejected_qty) * flt(d.conversion_factor), d.valuation_rate, is_submit, rejected = 1)

		self.bk_flush_supp_wh(is_submit)

		if self.values:
			get_obj('Stock Ledger', 'Stock Ledger').update_stock(self.values)


	# make Stock Entry
	def make_sl_entry(self, d, wh, qty, in_value, is_submit, rejected = 0):
		if rejected:
			serial_no = cstr(d.rejected_serial_no).strip()
		else:
			serial_no = cstr(d.serial_no).strip()

		self.values.append({
			'item_code'					: d.fields.has_key('item_code') and d.item_code or d.rm_item_code,
			'warehouse'					: wh,
			'posting_date'				: self.doc.posting_date,
			'posting_time'				: self.doc.posting_time,
			'voucher_type'				: 'Purchase Receipt',
			'voucher_no'				: self.doc.name,
			'voucher_detail_no'			: d.name,
			'actual_qty'				: qty,
			'stock_uom'					: d.stock_uom,
			'incoming_rate'				: in_value,
			'company'					: self.doc.company,
			'fiscal_year'				: self.doc.fiscal_year,
			'is_cancelled'				: (is_submit==1) and 'No' or 'Yes',
			'batch_no'					: cstr(d.batch_no).strip(),
			'serial_no'					: serial_no
			})


	def validate_inspection(self):
		for d in getlist(self.doclist, 'purchase_receipt_details'):		 #Enter inspection date for all items that require inspection
			ins_reqd = sql("select inspection_required from `tabItem` where name = %s", (d.item_code), as_dict = 1)
			ins_reqd = ins_reqd and ins_reqd[0]['inspection_required'] or 'No'
			if ins_reqd == 'Yes' and not d.qa_no:
				msgprint("Item: " + d.item_code + " requires QA Inspection. Please enter QA No or report to authorized person to create Quality Inspection")

	# Check for Stopped status
	def check_for_stopped_status(self, pc_obj):
		check_list =[]
		for d in getlist(self.doclist, 'purchase_receipt_details'):
			if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_docname not in check_list:
				check_list.append(d.prevdoc_docname)
				pc_obj.check_for_stopped_status( d.prevdoc_doctype, d.prevdoc_docname)

	# on submit
	def on_submit(self):
		purchase_controller = webnotes.get_obj("Purchase Common")
		purchase_controller.is_item_table_empty(self)

		# Check for Approving Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total)

		# Set status as Submitted
		webnotes.conn.set(self.doc,'status', 'Submitted')

		# Update Previous Doc i.e. update pending_qty and Status accordingly
		purchase_controller.update_prevdoc_detail(self, is_submit = 1)

		# Update Serial Record
		get_obj('Stock Ledger').update_serial_record(self, 'purchase_receipt_details', is_submit = 1, is_incoming = 1)

		# Update Stock
		self.update_stock(is_submit = 1)

		# Update last purchase rate
		purchase_controller.update_last_purchase_rate(self, 1)
		
		self.make_gl_entries()

	def check_next_docstatus(self):
		submit_rv = sql("select t1.name from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 where t1.name = t2.parent and t2.purchase_receipt = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_rv:
			msgprint("Purchase Invoice : " + cstr(self.submit_rv[0][0]) + " has already been submitted !")
			raise Exception , "Validation Error."


	def on_cancel(self):
		pc_obj = get_obj('Purchase Common')

		self.check_for_stopped_status(pc_obj)
		# 1.Check if Purchase Invoice has been submitted against current Purchase Order
		# pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Invoice', docname = self.doc.name, detail_doctype = 'Purchase Invoice Item')

		submitted = sql("select t1.name from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 where t1.name = t2.parent and t2.purchase_receipt = '%s' and t1.docstatus = 1" % self.doc.name)
		if submitted:
			msgprint("Purchase Invoice : " + cstr(submitted[0][0]) + " has already been submitted !")
			raise Exception

		# 2.Set Status as Cancelled
		webnotes.conn.set(self.doc,'status','Cancelled')

		# 3. Cancel Serial No
		get_obj('Stock Ledger').update_serial_record(self, 'purchase_receipt_details', is_submit = 0, is_incoming = 1)

		# 4.Update Bin
		self.update_stock(is_submit = 0)

		# 5.Update Material Requests Pending Qty and accordingly it's Status
		pc_obj.update_prevdoc_detail(self, is_submit = 0)

		# 6. Update last purchase rate
		pc_obj.update_last_purchase_rate(self, 0)
		
		self.make_gl_entries()

	def validate_for_subcontracting(self):
		if self.sub_contracted_items and self.purchase_items and not self.doc.is_subcontracted:
			webnotes.msgprint(_("""Please enter whether Purchase Recipt is made for subcontracting 
				or purchasing, in 'Is Subcontracted' field"""), raise_exception=1)
			
		if self.doc.is_subcontracted and not self.doc.supplier_warehouse:
			webnotes.msgprint(_("Please Enter Supplier Warehouse for subcontracted Items"), 
				raise_exception=1)
				
	def update_raw_materials_supplied(self):
		self.doclist = self.doc.clear_table(self.doclist, 'pr_raw_material_details')
		if self.sub_contracted_items:
			for item in self.doclist.get({"parentfield": "purchase_receipt_details"}):
				if item.item_code in self.sub_contracted_items:
					self.add_bom_items(item)

	def add_bom_items(self, d):
		bom_items = self.get_items_from_default_bom(d.item_code)
		raw_materials_cost = 0
		for item in bom_items:
			required_qty = flt(item.qty_consumed_per_unit) * flt(d.qty) * flt(d.conversion_factor)
			self.doclist.append({
				"parentfield": "pr_raw_material_details",
				"doctype": "Purchase Receipt Item Supplied",
				"reference_name": d.name,
				"bom_detail_no": item.name,
				"main_item_code": d.item_code,
				"rm_item_code": item.item_code,
				"description": item.description,
				"stock_uom": item.stock_uom,
				"required_qty": required_qty,
				"consumed_qty": required_qty,
				"conversion_factor": d.conversion_factor,
				"rate": item.rate,
				"amount": required_qty * flt(item.rate)
			})
			
			raw_materials_cost += required_qty * flt(item.rate)
			
		d.rm_supp_cost = raw_materials_cost

	def get_items_from_default_bom(self, item_code):
		# print webnotes.conn.sql("""select name from `tabBOM` where item = '_Test FG Item'""")
		bom_items = sql("""select t2.item_code, t2.qty_consumed_per_unit, 
			t2.rate, t2.stock_uom, t2.name, t2.description 
			from `tabBOM` t1, `tabBOM Item` t2 
			where t2.parent = t1.name and t1.item = %s and t1.is_default = 1 
			and t1.docstatus = 1 and t1.is_active = 1""", item_code, as_dict=1)
		if not bom_items:
			msgprint(_("No default BOM exists for item: ") + item_code, raise_exception=1)
		
		return bom_items

	def bk_flush_supp_wh(self, is_submit):
		for d in getlist(self.doclist, 'pr_raw_material_details'):
			# negative quantity is passed as raw material qty has to be decreased 
			# when PR is submitted and it has to be increased when PR is cancelled
			consumed_qty = - flt(d.consumed_qty)
			self.make_sl_entry(d, self.doc.supplier_warehouse, flt(consumed_qty), 0, is_submit)

	def get_current_stock(self):
		for d in getlist(self.doclist, 'pr_raw_material_details'):
			if self.doc.supplier_warehouse:
				bin = sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.rm_item_code, self.doc.supplier_warehouse), as_dict = 1)
				d.current_stock = bin and flt(bin[0]['actual_qty']) or 0


	def get_rate(self,arg):
		return get_obj('Purchase Common').get_rate(arg,self)
	
	def load_default_taxes(self):
		self.doclist = get_obj('Purchase Common').load_default_taxes(self)
	
	def get_purchase_tax_details(self):
		self.doclist = get_obj('Purchase Common').get_purchase_tax_details(self)
		
	def make_gl_entries(self):
		if not cint(webnotes.defaults.get_global_default("auto_inventory_accounting")):
			return
		
		abbr = webnotes.conn.get_value("Company", self.doc.company, "abbr")
		stock_received_account = "Stock Received But Not Billed - %s" % (abbr,)
		stock_in_hand_account = self.get_stock_in_hand_account()
		
		total_valuation_amount = self.get_total_valuation_amount()
		
		if total_valuation_amount:
			gl_entries = [
				# debit stock in hand account
				self.get_gl_dict({
					"account": stock_in_hand_account,
					"against": stock_received_account,
					"debit": total_valuation_amount,
					"remarks": self.doc.remarks or "Accounting Entry for Stock",
				}, self.doc.docstatus == 2),
			
				# credit stock received but not billed account
				self.get_gl_dict({
					"account": stock_received_account,
					"against": stock_in_hand_account,
					"credit": total_valuation_amount,
					"remarks": self.doc.remarks or "Accounting Entry for Stock",
				}, self.doc.docstatus == 2),
			]
			from accounts.general_ledger import make_gl_entries
			make_gl_entries(gl_entries, cancel=self.doc.docstatus == 2)
		
	def get_total_valuation_amount(self):
		total_valuation_amount = 0.0
		
		for item in self.doclist.get({"parentfield": "purchase_receipt_details"}):
			if item.item_code in self.stock_items:
				total_valuation_amount += flt(item.valuation_rate) * \
					flt(item.qty) * flt(item.conversion_factor)

		return total_valuation_amount