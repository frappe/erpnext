# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, nowdate, add_days
from frappe.model.mapper import get_mapped_doc

from erpnext.controllers.buying_controller import BuyingController
from erpnext.buying.utils import validate_for_items

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class SupplierQuotation(BuyingController):
	def validate(self):
		super(SupplierQuotation, self).validate()

		if not self.status:
			self.status = "Draft"

		from erpnext.controllers.status_updater import validate_status
		validate_status(self.status, ["Draft", "Submitted", "Stopped",
			"Cancelled"])

		validate_for_items(self)
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", "qty")

	def on_submit(self):
		frappe.db.set(self, "status", "Submitted")
		self.update_rfq_supplier_status(1)

	def on_cancel(self):
		frappe.db.set(self, "status", "Cancelled")
		self.update_rfq_supplier_status(0)

	def on_trash(self):
		pass

	def validate_with_previous_doc(self):
		super(SupplierQuotation, self).validate_with_previous_doc({
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
	def update_rfq_supplier_status(self, include_me):
		rfq_list = set([])
		for item in self.items:
			if item.request_for_quotation:
				rfq_list.add(item.request_for_quotation)
		for rfq in rfq_list:
			doc = frappe.get_doc('Request for Quotation', rfq)
			doc_sup = frappe.get_all('Request for Quotation Supplier', filters=
				{'parent': doc.name, 'supplier': self.supplier}, fields=['name', 'quote_status'])

			doc_sup = doc_sup[0] if doc_sup else None
			if not doc_sup:
				frappe.throw(_("Supplier {0} not found in {1}").format(self.supplier,
					"<a href='desk#Form/Request for Quotation/{0}'> Request for Quotation {0} </a>".format(doc.name)))

			quote_status = _('Received')
			for item in doc.items:
				sqi_count = frappe.db.sql("""
					SELECT
						COUNT(sqi.name) as count
					FROM
						`tabSupplier Quotation Item` as sqi,
						`tabSupplier Quotation` as sq
					WHERE sq.supplier = %(supplier)s
						AND sqi.docstatus = 1
						AND sq.name != %(me)s
						AND sqi.request_for_quotation_item = %(rqi)s
						AND sqi.parent = sq.name""",
					{"supplier": self.supplier, "rqi": item.name, 'me': self.name}, as_dict=1)[0]
				self_count = sum(my_item.request_for_quotation_item == item.name
					for my_item in self.items) if include_me else 0
				if (sqi_count.count + self_count) == 0:
					quote_status = _('Pending')
			if quote_status == _('Received') and doc_sup.quote_status == _('No Quote'):
				frappe.msgprint(_("{0} indicates that {1} will not provide a quotation, but all items \
					have been quoted. Updating the RFQ quote status.").format(doc.name, self.supplier))
				frappe.db.set_value('Request for Quotation Supplier', doc_sup.name, 'quote_status', quote_status)
				frappe.db.set_value('Request for Quotation Supplier', doc_sup.name, 'no_quote', 0)
			elif doc_sup.quote_status != _('No Quote'):
				frappe.db.set_value('Request for Quotation Supplier', doc_sup.name, 'quote_status', quote_status)

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Supplier Quotation'),
	})

	return list_context

@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("get_schedule_dates")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)

	doclist = get_mapped_doc("Supplier Quotation", source_name,		{
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
				["material_request", "material_request"],
				["material_request_item", "material_request_item"],
				["sales_order", "sales_order"]
			],
			"postprocess": update_item
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
		},
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Supplier Quotation", source_name, {
		"Supplier Quotation": {
			"doctype": "Quotation",
			"field_map": {
				"name": "supplier_quotation",
			}
		},
		"Supplier Quotation Item": {
			"doctype": "Quotation Item",
			"condition": lambda doc: frappe.db.get_value("Item", doc.item_code, "is_sales_item")==1,
			"add_if_empty": True
		}
	}, target_doc)

	return doclist
