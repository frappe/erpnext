# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
# from frappe.model.mapper import get_mapped_doc
from frappe.model.mapper import get_mapped_doc, map_child_doc
from erpnext.stock.get_item_details import get_conversion_factor
from frappe.utils import floor, flt, today, cint
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as create_delivery_note_from_sales_order

class BulkDeliveryNotefromPickListCreationTool(Document):
	@frappe.whitelist()
	def get_options(self, arg=None):
		if frappe.get_meta("Delivery Note").get_field("naming_series"):
			return frappe.get_meta("Delivery Note").get_field("naming_series").options

	@frappe.whitelist()
	def get_pl(self):
		conditions = ""
		if self.company:
			conditions +="AND pl.company = %s" % frappe.db.escape(self.company)

		if self.customer:
			conditions +="AND pl.customer = %s" % frappe.db.escape(self.customer)

		query = frappe.db.sql(""" select 
			pl.customer,
			c.customer_name,
			pl.name

			from `tabPick List` pl 
			join `tabCustomer` c on pl.customer = c.name
			where pl.docstatus = 1 AND pl.delivery_note_done = 0 AND pl.purpose = "Delivery"
			{conditions} """.format(conditions=conditions), as_dict=1)

		return query





	@frappe.whitelist()
	def create_delivery_note(self, target_doc=None):
		for i in self.pick_lists:
			pick_list = frappe.get_doc('Pick List', i.pick_list)
			validate_item_locations(pick_list)

			sales_orders = [d.sales_order for d in pick_list.locations if d.sales_order]
			sales_orders = set(sales_orders)

			delivery_note = None
			for sales_order in sales_orders:
				delivery_note = create_delivery_note_from_sales_order(sales_order,
					delivery_note, skip_item_mapping=True)

			# map rows without sales orders as well
			if not delivery_note:
				delivery_note = frappe.new_doc("Delivery Note")
			item_table_mapper = {
				'doctype': 'Delivery Note Item',
				'field_map': {
					'rate': 'rate',
					'name': 'so_detail',
					'parent': 'against_sales_order',
				},
				'condition': lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
			}

			item_table_mapper_without_so = {
				'doctype': 'Delivery Note Item',
				'field_map': {
					'rate': 'rate',
					'name': 'name',
					'parent': '',
				}
			}

			for location in pick_list.locations:
				if location.sales_order_item:
					sales_order_item = frappe.get_cached_doc('Sales Order Item', {'name':location.sales_order_item})
				else:
					sales_order_item = None

				source_doc, table_mapper = [sales_order_item, item_table_mapper] if sales_order_item \
					else [location, item_table_mapper_without_so]

				dn_item = map_child_doc(source_doc, delivery_note, table_mapper)

				if dn_item:
					dn_item.warehouse = location.warehouse
					dn_item.qty = flt(location.picked_qty) / (flt(location.conversion_factor) or 1)
					dn_item.batch_no = location.batch_no
					dn_item.serial_no = location.serial_no

					update_delivery_note_item(source_doc, dn_item, delivery_note)

			set_delivery_note_missing_values(delivery_note)

			delivery_note.pick_list = pick_list.name
			delivery_note.customer = pick_list.customer if pick_list.customer else None

			delivery_note.insert()
	# @frappe.whitelist()
	# def create_delivery_note(self):
# 		for line in self.pick_lists:
# 			if line.customer:
# 				doc = frappe.new_doc("Delivery Note")
# 				doc.customer = line.customer
# 				doc.company = self.company
# 				doc.pick_list = line.pick_list
# 				expense_account = frappe.get_cached_value('Company', self.company, 'stock_adjustment_account')
# 				cost_center = frappe.get_cached_value('Company', self.company, 'cost_center')
# 				pick_list = frappe.get_doc("Pick List",line.pick_list)
# 				for itm in pick_list.locations:
# 					rate = 0.0
# 					if itm.sales_order_item:
# 						sale_line = frappe.get_doc("Sales Order Item",itm.sales_order_item)
# 						rate =sale_line.rate
# 					doc.append("items", {
# 						"item_name": itm.item_name,
# 						"item_code": itm.item_code,
# 						"description": itm.description,
# 						"qty": itm.qty,
# 						"uom": itm.uom,
# 						"stock_uom": itm.stock_uom,
# 						"conversion_factor": itm.conversion_factor,
# 						"rate": rate,
# 						"warehouse": itm.warehouse,
# 						"against_sales_order": itm.sales_order,
# 						"so_detail": itm.sales_order_item,
# 						"cost_center": cost_center,
# 						"expense_account": expense_account
# 					})
# 				set_delivery_note_missing_values(doc)
# 				doc.insert()
# 				doc.save()
# 				lst=frappe.get_doc("Delivery Note",doc.name)
# 				for i in lst.items:
# 					d=frappe.get_doc("Sales Order",i.against_sales_order)
# 					lst.set_warehouse = d.set_warehouse
# 					lst.tax_category = d.tax_category
# 					lst.shipping_address_name = d.shipping_address_name
# 					lst.customer_gstin = d.customer_gstin
# 					lst.company_address = d.company_address
# 					lst.contact_person =d.contact_person
# 					lst.shipping_rule = d.shipping_rule
# 					lst.taxes_and_charges = d.taxes_and_charges
# 					lst.apply_discount_on = d.apply_discount_on
# 					lst.additional_discount_percentage = d.additional_discount_percentage
# 					lst.cost_center=d.cost_center
# 					for tax in d.taxes:
# 						lst.append("taxes",{
# 							"charge_type":tax.charge_type,
# 							"account_head":tax.account_head,
# 							"description":tax.description,
# 							"included_in_print_rate":tax.included_in_print_rate,
# 							"cost_center":tax.cost_center,
# 							"rate":tax.rate,
# 							"tax_amount":tax.tax_amount,
# 							"tax_amount":tax.total,
# 							"tax_amount_after_discount_amount":tax.tax_amount_after_discount_amount,
# 							"base_tax_amount":tax.base_tax_amount,
# 							"base_total":tax.base_total,
# 							"base_tax_amount_after_discount_amount":tax.base_tax_amount_after_discount_amount,
# 							"item_wise_tax_detail":tax.item_wise_tax_detail
# 						})
# 				lst.save()

def validate_item_locations(pick_list):
	if not pick_list.locations:
		frappe.throw(_("Add items in the Item Locations table"))


def set_delivery_note_missing_values(target):
	target.run_method('set_missing_values')
	target.run_method('set_po_nos')
	target.run_method('calculate_taxes_and_totals')

def update_delivery_note_item(source, target, delivery_note):
	cost_center = frappe.db.get_value('Project', delivery_note.project, 'cost_center')
	if not cost_center:
		cost_center = get_cost_center(source.item_code, 'Item', delivery_note.company)

	if not cost_center:
		cost_center = get_cost_center(source.item_group, 'Item Group', delivery_note.company)

	target.cost_center = cost_center

def get_cost_center(for_item, from_doctype, company):
	'''Returns Cost Center for Item or Item Group'''
	return frappe.db.get_value('Item Default',
		fieldname=['buying_cost_center'],
		filters={
			'parent': for_item,
			'parenttype': from_doctype,
			'company': company
		})

# @frappe.whitelist()
# def make_delivery_note(source_name, target_doc=None, skip_item_mapping=False):
# 	def set_item_in_delivery_note(source, target):
# 		pick_list = frappe.get_doc(source)
# 		bulk = frappe.get_doc(target)

# 		bulk.append('pick_lists',{
# 			"customer":pick_list.customer,
# 			"pick_list":pick_list.name
# 		})

# 	doclist = get_mapped_doc("Pick List", source_name, {
# 		"Pick List": {
# 			"doctype": "Bulk Delivery Note from Pick List Creation Tool",
# 			"validation": {
# 				"docstatus": ["=", 1],
# 				"delivery_note_done": ['=',0],
# 				"purpose": "Delivery"
# 			},

# 		}
# 	}, target_doc, set_item_in_delivery_note)
# 	return doclist