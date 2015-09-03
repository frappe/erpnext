# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, flt, cint
from frappe import _


from frappe.model.document import Document

class StockUOMReplaceUtility(Document):
	
	# Update Stock UOM
	def update_stock_uom(self):
		self.validate_item()
		self.validate_mandatory()
		self.validate_uom_integer_type()
		
		update_stock_ledger_entry(self.item_code, self.new_stock_uom, self.conversion_factor)
		update_bin(self.item_code, self.new_stock_uom, self.conversion_factor)
		update_item_master(self.item_code, self.new_stock_uom, self.conversion_factor)
		
		#if item is template change UOM for all associated variants
		if frappe.db.get_value("Item", self.item_code, "has_variants"):
			for d in frappe.db.get_all("Item", filters= {"variant_of": self.item_code}):
				update_stock_ledger_entry(d.name, self.new_stock_uom, self.conversion_factor)
				update_bin(d.name, self.new_stock_uom, self.conversion_factor)
				update_item_master(d.name, self.new_stock_uom, self.conversion_factor)
		
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

		# check conversion factor
		if not flt(self.conversion_factor):
			frappe.throw(_("Conversion Factor is required"))

		stock_uom = frappe.db.get_value("Item", self.item_code, "stock_uom")
		if cstr(self.new_stock_uom) == cstr(stock_uom):
			frappe.throw(_("Item is updated"))
		
	def validate_uom_integer_type(self):
		current_is_integer = frappe.db.get_value("UOM", self.current_stock_uom, "must_be_whole_number")
		new_is_integer = frappe.db.get_value("UOM", self.new_stock_uom, "must_be_whole_number")

		if not current_is_integer and new_is_integer:
			frappe.throw(_("New UOM must NOT be of type Whole Number"))

		if current_is_integer and new_is_integer and cint(self.conversion_factor)!=self.conversion_factor:
			frappe.throw(_("Conversion factor cannot be in fractions"))

def update_item_master(item_code, new_stock_uom, conversion_factor):
	frappe.db.set_value("Item", item_code, "stock_uom", new_stock_uom)
	frappe.msgprint(_("Stock UOM updated for Item {0}").format(item_code))

def update_bin(item_code, new_stock_uom, conversion_factor):
	# update bin
	if flt(conversion_factor) != flt(1):
		frappe.db.sql("""update `tabBin`
			set stock_uom = %s,
				indented_qty = ifnull(indented_qty,0) * %s,
				ordered_qty = ifnull(ordered_qty,0) * %s,
				reserved_qty = ifnull(reserved_qty,0) * %s,
				planned_qty = ifnull(planned_qty,0) * %s,
				projected_qty = actual_qty + ordered_qty + indented_qty +
					planned_qty - reserved_qty
			where item_code = %s""", (new_stock_uom, conversion_factor,
				conversion_factor, conversion_factor,
				conversion_factor, item_code))
	else:
		frappe.db.sql("update `tabBin` set stock_uom = %s where item_code = %s",
			 (new_stock_uom, item_code) )

def update_stock_ledger_entry(item_code, new_stock_uom, conversion_factor):
	# update stock ledger entry
	from erpnext.stock.stock_ledger import update_entries_after

	if flt(conversion_factor) != flt(1):
		frappe.db.sql("""update `tabStock Ledger Entry`
			set 
				stock_uom = %s, 
				actual_qty = ifnull(actual_qty,0) * %s,
				qty_after_transaction = ifnull(qty_after_transaction, 0) * %s
			where item_code = %s""",
			(new_stock_uom, conversion_factor, conversion_factor, item_code))
	else:
		frappe.db.sql("""update `tabStock Ledger Entry` set stock_uom=%s
			where item_code=%s""", (new_stock_uom, item_code))

	# acknowledge user
	frappe.msgprint(_("Stock Ledger entries balances updated"))

	# update item valuation
	if flt(conversion_factor) != flt(1):
		wh = frappe.db.sql("select name from `tabWarehouse`")
		for w in wh:
			update_entries_after({"item_code": item_code, "warehouse": w[0]})

	# acknowledge user
	frappe.msgprint(_("Item valuation updated"))

@frappe.whitelist()
def get_stock_uom(item_code):
	return { 'current_stock_uom': cstr(frappe.db.get_value('Item', item_code, 'stock_uom')) }

