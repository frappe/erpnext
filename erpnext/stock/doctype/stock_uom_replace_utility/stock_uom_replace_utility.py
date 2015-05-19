# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, flt, cint
from frappe import _


from frappe.model.document import Document

class StockUOMReplaceUtility(Document):
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

	def update_item_master(self):
		item_doc = frappe.get_doc("Item", self.item_code)
		item_doc.stock_uom = self.new_stock_uom
		item_doc.save()

		frappe.msgprint(_("Stock UOM updated for Item {0}").format(self.item_code))

	def update_bin(self):
		# update bin
		if flt(self.conversion_factor) != flt(1):
			frappe.db.sql("""update `tabBin`
				set stock_uom = %s,
					indented_qty = ifnull(indented_qty,0) * %s,
					ordered_qty = ifnull(ordered_qty,0) * %s,
					reserved_qty = ifnull(reserved_qty,0) * %s,
					planned_qty = ifnull(planned_qty,0) * %s,
					projected_qty = actual_qty + ordered_qty + indented_qty +
						planned_qty - reserved_qty
				where item_code = %s""", (self.new_stock_uom, self.conversion_factor,
					self.conversion_factor, self.conversion_factor,
					self.conversion_factor, self.item_code))
		else:
			frappe.db.sql("update `tabBin` set stock_uom = %s where item_code = %s",
				 (self.new_stock_uom, self.item_code) )

		# acknowledge user
		frappe.msgprint(_("Stock balances updated"))

	def update_stock_ledger_entry(self):
		# update stock ledger entry
		from erpnext.stock.stock_ledger import update_entries_after

		if flt(self.conversion_factor) != flt(1):
			frappe.db.sql("""update `tabStock Ledger Entry`
				set stock_uom = %s, actual_qty = ifnull(actual_qty,0) * %s
				where item_code = %s""",
				(self.new_stock_uom, self.conversion_factor, self.item_code))
		else:
			frappe.db.sql("""update `tabStock Ledger Entry` set stock_uom=%s
				where item_code=%s""", (self.new_stock_uom, self.item_code))

		# acknowledge user
		frappe.msgprint(_("Stock Ledger entries balances updated"))

		# update item valuation
		if flt(self.conversion_factor) != flt(1):
			wh = frappe.db.sql("select name from `tabWarehouse`")
			for w in wh:
				update_entries_after({"item_code": self.item_code, "warehouse": w[0]})

		# acknowledge user
		frappe.msgprint(_("Item valuation updated"))

	# Update Stock UOM
	def update_stock_uom(self):
		self.validate_mandatory()
		self.validate_uom_integer_type()

		self.update_stock_ledger_entry()

		self.update_bin()

		self.update_item_master()


	def validate_uom_integer_type(self):
		current_is_integer = frappe.db.get_value("UOM", self.current_stock_uom, "must_be_whole_number")
		new_is_integer = frappe.db.get_value("UOM", self.new_stock_uom, "must_be_whole_number")

		if not current_is_integer and new_is_integer:
			frappe.throw(_("New UOM must NOT be of type Whole Number"))

		if current_is_integer and new_is_integer and cint(self.conversion_factor)!=self.conversion_factor:
			frappe.throw(_("Conversion factor cannot be in fractions"))

@frappe.whitelist()
def get_stock_uom(item_code):
	return { 'current_stock_uom': cstr(frappe.db.get_value('Item', item_code, 'stock_uom')) }

