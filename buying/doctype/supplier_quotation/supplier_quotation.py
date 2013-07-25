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
from webnotes.model.code import get_obj

from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=None):
		self.doc, self.doclist = doc, doclist or []
		self.tname, self.fname = "Supplier Quotation Item", "quotation_items"
		
	def validate(self):
		super(DocType, self).validate()
		
		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Stopped", 
			"Cancelled"])
		
		self.validate_common()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", "qty")

	def on_submit(self):
		purchase_controller = webnotes.get_obj("Purchase Common")
		purchase_controller.is_item_table_empty(self)
		
		webnotes.conn.set(self.doc, "status", "Submitted")

	def on_cancel(self):
		webnotes.conn.set(self.doc, "status", "Cancelled")
		
	def on_trash(self):
		pass
			
	def validate_with_previous_doc(self):
		super(DocType, self).validate_with_previous_doc(self.tname, {
			"Material Request": {
				"ref_dn_field": "prevdoc_docname",
				"compare_fields": [["company", "="]],
			},
			"Material Request Item": {
				"ref_dn_field": "prevdoc_detail_docname",
				"compare_fields": [["item_code", "="], ["uom", "="]],
				"is_child_table": True
			}
		})

			
	def validate_common(self):
		pc = get_obj('Purchase Common')
		pc.validate_for_items(self)
		pc.get_prevdoc_date(self)

@webnotes.whitelist()
def make_purchase_order(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
	
	def set_missing_values(source, target):
		bean = webnotes.bean(target)
		bean.run_method("set_missing_values")
		bean.run_method("get_schedule_dates")

	def update_item(obj, target, source_parent):
		target.conversion_factor = 1

	doclist = get_mapped_doclist("Supplier Quotation", source_name,		{
		"Supplier Quotation": {
			"doctype": "Purchase Order", 
			"validation": {
				"docstatus": ["=", 1],
			}
		}, 
		"Supplier Quotation Item": {
			"doctype": "Purchase Order Item", 
			"field_map": [
				["name", "supplier_quotation_item"], 
				["parent", "supplier_quotation"], 
				["uom", "stock_uom"],
				["uom", "uom"],
				["prevdoc_detail_docname", "prevdoc_detail_docname"],
				["prevdoc_doctype", "prevdoc_doctype"],
				["prevdoc_docname", "prevdoc_docname"]
			],
			"postprocess": update_item
		}, 
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges", 
			"add_if_empty": True
		},
	}, target_doclist, set_missing_values)

	return [d.fields for d in doclist]