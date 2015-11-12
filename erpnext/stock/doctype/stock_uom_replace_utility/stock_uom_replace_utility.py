# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, flt, cint
from frappe import _
from erpnext.stock.stock_ledger import update_entries_after

from frappe.model.document import Document

class StockUOMReplaceUtility(Document):	
	def update_stock_uom(self):
		self.validate_item()
		self.validate_mandatory()
		self.validate_uom_integer_type()
		
		self.update_stock_ledger_entry(self.item_code)
		self.update_bin(self.item_code)
		self.update_item_master(self.item_code)
		
		#if item is template change UOM for all associated variants
		if frappe.db.get_value("Item", self.item_code, "has_variants"):
			for d in frappe.db.get_all("Item", filters= {"variant_of": self.item_code}):
				self.update_bin(d.name)
				self.update_stock_ledger_entry(d.name)
				self.update_item_master(d.name)
		
	def validate_item(self):
		if frappe.db.get_value("Item", self.item_code, "variant_of"):
			frappe.throw(_("You cannot change default UOM of Variant. To change default UOM for Variant change default UOM of the Template"))
		
	def validate_mandatory(self):
		if not cstr(self.item_code):
			frappe.throw(_("Item is required"))

		if not cstr(self.new_stock_uom):
			frappe.throw(_("New Stock UOM is required"))

		if cstr(self.current_stock_uom) == cstr(self.new_stock_uom):
			frappe.throw(_("New Stock UOM must be different from current stock UOM"))

		if not flt(self.conversion_factor):
			frappe.throw(_("Conversion Factor is required"))

		stock_uom = frappe.db.get_value("Item", self.item_code, "stock_uom")
		if cstr(self.new_stock_uom) == cstr(stock_uom):
			frappe.throw(_("Item is already updated with new Stock UOM {0}").format(self.new_stock_uom))
		
	def validate_uom_integer_type(self):
		current_is_integer = frappe.db.get_value("UOM", self.current_stock_uom, "must_be_whole_number")
		new_is_integer = frappe.db.get_value("UOM", self.new_stock_uom, "must_be_whole_number")

		if not current_is_integer and new_is_integer:
			frappe.throw(_("New UOM must NOT be of type Whole Number"))

		if current_is_integer and new_is_integer and cint(self.conversion_factor)!=self.conversion_factor:
			frappe.throw(_("Conversion factor cannot be in fractions"))
			
	def update_bin(self, item_code):
		if flt(self.conversion_factor) != flt(1):
			frappe.db.sql("""update `tabBin`
				set stock_uom = %(stock_uom)s,
					indented_qty = ifnull(indented_qty,0) * %(conversion_factor)s,
					ordered_qty = ifnull(ordered_qty,0) * %(conversion_factor)s,
					reserved_qty = ifnull(reserved_qty,0) * %(conversion_factor)s,
					planned_qty = ifnull(planned_qty,0) * %(conversion_factor)s,
					projected_qty = actual_qty + ordered_qty + indented_qty +
						planned_qty - reserved_qty
				where item_code = %(item_code)s""", {
					"item_code": item_code,
					"stock_uom": self.new_stock_uom,
					"conversion_factor": self.conversion_factor
				})
		else:
			frappe.db.sql("update `tabBin` set stock_uom = %s where item_code = %s", 
				(self.new_stock_uom, item_code))

	def update_stock_ledger_entry(self, item_code):
		if flt(self.conversion_factor) != flt(1):
			# Update SLE
			frappe.db.sql("""update `tabStock Ledger Entry`
				set 
					stock_uom = %(stock_uom)s, 
					actual_qty = ifnull(actual_qty,0) * %(conversion_factor)s,
					qty_after_transaction = ifnull(qty_after_transaction, 0) * %(conversion_factor)s,
					incoming_rate = incoming_rate / %(conversion_factor)s,
					outgoing_rate = outgoing_rate / %(conversion_factor)s,
					valuation_rate = if(voucher_type='Stock Reconciliation', 
						valuation_rate / %(conversion_factor)s, valuation_rate)
				where item_code = %(item_code)s""", {
					"item_code": item_code,
					"stock_uom": self.new_stock_uom,
					"conversion_factor": self.conversion_factor
				})
		
			# Repost SLE to update item valuation and bin qty
			wh = frappe.db.sql("""select distinct warehouse from `tabStock Ledger Entry` 
				where item_code=%s""", item_code)
			for w in wh:
				update_entries_after({"item_code": item_code, "warehouse": w[0]})
		else:
			frappe.db.sql("""update `tabStock Ledger Entry` set stock_uom=%s
				where item_code=%s""", (self.new_stock_uom, item_code))

		# acknowledge user
		frappe.msgprint(_("Stock Ledger Entries updated"))
		
	def update_item_master(self, item_code):
		frappe.db.set_value("Item", item_code, "stock_uom", self.new_stock_uom)

		frappe.db.sql("delete from `tabUOM Conversion Detail` where uom=%s and parent=%s",
			(self.new_stock_uom, item_code))
		frappe.db.sql("update `tabUOM Conversion Detail` set uom=%s where uom=%s and parent=%s",
			(self.new_stock_uom, self.current_stock_uom, item_code))

		frappe.db.sql("""
			update `tabUOM Conversion Detail`
			set conversion_factor = conversion_factor * %s
			where uom != %s and parent=%s
		""", (self.conversion_factor, self.new_stock_uom, item_code))

		frappe.msgprint(_("Stock UOM updated in Item {0}").format(item_code))

@frappe.whitelist()
def get_stock_uom(item_code):
	return { 'current_stock_uom': cstr(frappe.db.get_value('Item', item_code, 'stock_uom')) }

