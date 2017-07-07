# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
import frappe.utils
from frappe.utils import cstr, flt, getdate, comma_and, cint
from frappe import _
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.stock_balance import update_bin_qty, get_reserved_qty
from frappe.desk.notifications import clear_doctype_notifications
from erpnext.controllers.recurring_document import month_map, get_next_date

from erpnext.controllers.selling_controller import SellingController

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class WarehouseRequired(frappe.ValidationError): pass

class SalesOrder(SellingController):
	def __init__(self, arg1, arg2=None):
		super(SalesOrder, self).__init__(arg1, arg2)

	def validate(self):
		super(SalesOrder, self).validate()

		self.validate_order_type()
		self.validate_delivery_date()
		self.validate_mandatory()
		self.validate_proj_cust()
		self.validate_po()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_for_items()
		self.validate_warehouse()
		self.validate_drop_ship()

		from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
		make_packing_list(self)

		self.validate_with_previous_doc()
		self.set_status()

		if not self.billing_status: self.billing_status = 'Not Billed'
		if not self.delivery_status: self.delivery_status = 'Not Delivered'

	def validate_mandatory(self):
		# validate transaction date v/s delivery date
		if self.delivery_date:
			if getdate(self.transaction_date) > getdate(self.delivery_date):
				frappe.msgprint(_("Expected Delivery Date is be before Sales Order Date"),
					indicator='orange',
					title=_('Warning'))

	def validate_po(self):
		# validate p.o date v/s delivery date
		if self.po_date and self.delivery_date and getdate(self.po_date) > getdate(self.delivery_date):
			frappe.throw(_("Expected Delivery Date cannot be before Purchase Order Date"))

		if self.po_no and self.customer:
			so = frappe.db.sql("select name from `tabSales Order` \
				where ifnull(po_no, '') = %s and name != %s and docstatus < 2\
				and customer = %s", (self.po_no, self.name, self.customer))
			if so and so[0][0] and not \
				cint(frappe.db.get_single_value("Selling Settings", "allow_against_multiple_purchase_orders")):
				frappe.msgprint(_("Warning: Sales Order {0} already exists against Customer's Purchase Order {1}").format(so[0][0], self.po_no))

	def validate_for_items(self):
		check_list = []
		for d in self.get('items'):
			check_list.append(cstr(d.item_code))

			# used for production plan
			d.transaction_date = self.transaction_date

			tot_avail_qty = frappe.db.sql("select projected_qty from `tabBin` \
				where item_code = %s and warehouse = %s", (d.item_code,d.warehouse))
			d.projected_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0

		# check for same entry multiple times
		unique_chk_list = set(check_list)
		if len(unique_chk_list) != len(check_list) and \
			not cint(frappe.db.get_single_value("Selling Settings", "allow_multiple_items")):
			frappe.msgprint(_("Same item has been entered multiple times"),
				title=_("Warning"), indicator='orange')

	def product_bundle_has_stock_item(self, product_bundle):
		"""Returns true if product bundle has stock item"""
		ret = len(frappe.db.sql("""select i.name from tabItem i, `tabProduct Bundle Item` pbi
			where pbi.parent = %s and pbi.item_code = i.name and i.is_stock_item = 1""", product_bundle))
		return ret

	def validate_sales_mntc_quotation(self):
		for d in self.get('items'):
			if d.prevdoc_docname:
				res = frappe.db.sql("select name from `tabQuotation` where name=%s and order_type = %s", (d.prevdoc_docname, self.order_type))
				if not res:
					frappe.msgprint(_("Quotation {0} not of type {1}").format(d.prevdoc_docname, self.order_type))

	def validate_order_type(self):
		super(SalesOrder, self).validate_order_type()

	def validate_delivery_date(self):
		if self.order_type == 'Sales' and not self.delivery_date:
			frappe.throw(_("Please enter 'Expected Delivery Date'"))

		self.validate_sales_mntc_quotation()

	def validate_proj_cust(self):
		if self.project and self.customer_name:
			res = frappe.db.sql("""select name from `tabProject` where name = %s
				and (customer = %s or ifnull(customer,'')='')""",
					(self.project, self.customer))
			if not res:
				frappe.throw(_("Customer {0} does not belong to project {1}").format(self.customer, self.project))

	def validate_warehouse(self):
		super(SalesOrder, self).validate_warehouse()

		for d in self.get("items"):
			if (frappe.db.get_value("Item", d.item_code, "is_stock_item")==1 or
				(self.has_product_bundle(d.item_code) and self.product_bundle_has_stock_item(d.item_code))) \
				and not d.warehouse and not cint(d.delivered_by_supplier):
				frappe.throw(_("Delivery warehouse required for stock item {0}").format(d.item_code),
					WarehouseRequired)

	def validate_with_previous_doc(self):
		super(SalesOrder, self).validate_with_previous_doc({
			"Quotation": {
				"ref_dn_field": "prevdoc_docname",
				"compare_fields": [["company", "="], ["currency", "="]]
			}
		})


	def update_enquiry_status(self, prevdoc, flag):
		enq = frappe.db.sql("select t2.prevdoc_docname from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.name=%s", prevdoc)
		if enq:
			frappe.db.sql("update `tabOpportunity` set status = %s where name=%s",(flag,enq[0][0]))

	def update_prevdoc_status(self, flag):
		for quotation in list(set([d.prevdoc_docname for d in self.get("items")])):
			if quotation:
				doc = frappe.get_doc("Quotation", quotation)
				if doc.docstatus==2:
					frappe.throw(_("Quotation {0} is cancelled").format(quotation))

				doc.set_status(update=True)
				doc.update_opportunity()

	def validate_drop_ship(self):
		for d in self.get('items'):
			if d.delivered_by_supplier and not d.supplier:
				frappe.throw(_("Row #{0}: Set Supplier for item {1}").format(d.idx, d.item_code))

	def on_submit(self):
		self.check_credit_limit()
		self.update_reserved_qty()

		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype, self.company, self.base_grand_total, self)
		self.update_project()
		self.update_prevdoc_status('submit')

	def on_cancel(self):
		# Cannot cancel closed SO
		if self.status == 'Closed':
			frappe.throw(_("Closed order cannot be cancelled. Unclose to cancel."))

		self.check_nextdoc_docstatus()
		self.update_reserved_qty()
		self.update_project()
		self.update_prevdoc_status('cancel')

		frappe.db.set(self, 'status', 'Cancelled')

	def update_project(self):
		project_list = []
		if self.project:
				project = frappe.get_doc("Project", self.project)
				project.flags.dont_sync_tasks = True
				project.update_sales_costing()
				project.save()
				project_list.append(self.project)

	def check_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit
		check_credit_limit(self.customer, self.company)

	def check_nextdoc_docstatus(self):
		# Checks Delivery Note
		submit_dn = frappe.db.sql_list("""select t1.name from `tabDelivery Note` t1,`tabDelivery Note Item` t2
			where t1.name = t2.parent and t2.against_sales_order = %s and t1.docstatus = 1""", self.name)
		if submit_dn:
			frappe.throw(_("Delivery Notes {0} must be cancelled before cancelling this Sales Order").format(comma_and(submit_dn)))

		# Checks Sales Invoice
		submit_rv = frappe.db.sql_list("""select t1.name
			from `tabSales Invoice` t1,`tabSales Invoice Item` t2
			where t1.name = t2.parent and t2.sales_order = %s and t1.docstatus = 1""",
			self.name)
		if submit_rv:
			frappe.throw(_("Sales Invoice {0} must be cancelled before cancelling this Sales Order").format(comma_and(submit_rv)))

		#check maintenance schedule
		submit_ms = frappe.db.sql_list("""select t1.name from `tabMaintenance Schedule` t1,
			`tabMaintenance Schedule Item` t2
			where t2.parent=t1.name and t2.sales_order = %s and t1.docstatus = 1""", self.name)
		if submit_ms:
			frappe.throw(_("Maintenance Schedule {0} must be cancelled before cancelling this Sales Order").format(comma_and(submit_ms)))

		# check maintenance visit
		submit_mv = frappe.db.sql_list("""select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
			where t2.parent=t1.name and t2.prevdoc_docname = %s and t1.docstatus = 1""",self.name)
		if submit_mv:
			frappe.throw(_("Maintenance Visit {0} must be cancelled before cancelling this Sales Order").format(comma_and(submit_mv)))

		# check production order
		pro_order = frappe.db.sql_list("""select name from `tabProduction Order`
			where sales_order = %s and docstatus = 1""", self.name)
		if pro_order:
			frappe.throw(_("Production Order {0} must be cancelled before cancelling this Sales Order").format(comma_and(pro_order)))

	def check_modified_date(self):
		mod_db = frappe.db.get_value("Sales Order", self.name, "modified")
		date_diff = frappe.db.sql("select TIMEDIFF('%s', '%s')" %
			( mod_db, cstr(self.modified)))
		if date_diff and date_diff[0][0]:
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name))

	def update_status(self, status):
		self.check_modified_date()
		self.set_status(update=True, status=status)
		self.update_reserved_qty()
		self.notify_update()
		clear_doctype_notifications(self)

	def update_reserved_qty(self, so_item_rows=None):
		"""update requested qty (before ordered_qty is updated)"""
		item_wh_list = []
		def _valid_for_reserve(item_code, warehouse):
			if item_code and warehouse and [item_code, warehouse] not in item_wh_list \
				and frappe.db.get_value("Item", item_code, "is_stock_item"):
					item_wh_list.append([item_code, warehouse])

		for d in self.get("items"):
			if (not so_item_rows or d.name in so_item_rows) and not d.delivered_by_supplier:
				if self.has_product_bundle(d.item_code):
					for p in self.get("packed_items"):
						if p.parent_detail_docname == d.name and p.parent_item == d.item_code:
							_valid_for_reserve(p.item_code, p.warehouse)
				else:
					_valid_for_reserve(d.item_code, d.warehouse)

		for item_code, warehouse in item_wh_list:
			update_bin_qty(item_code, warehouse, {
				"reserved_qty": get_reserved_qty(item_code, warehouse)
			})

	def on_update(self):
		pass

	def before_update_after_submit(self):
		self.validate_po()
		self.validate_drop_ship()
		self.validate_supplier_after_submit()

	def validate_supplier_after_submit(self):
		"""Check that supplier is the same after submit if PO is already made"""
		exc_list = []

		for item in self.items:
			if item.supplier:
				supplier = frappe.db.get_value("Sales Order Item", {"parent": self.name, "item_code": item.item_code},
					"supplier")
				if item.ordered_qty > 0.0 and item.supplier != supplier:
					exc_list.append(_("Row #{0}: Not allowed to change Supplier as Purchase Order already exists").format(item.idx))

		if exc_list:
			frappe.throw('\n'.join(exc_list))

	def update_delivery_status(self):
		"""Update delivery status from Purchase Order for drop shipping"""
		tot_qty, delivered_qty = 0.0, 0.0

		for item in self.items:
			if item.delivered_by_supplier:
				item_delivered_qty  = frappe.db.sql("""select sum(qty)
					from `tabPurchase Order Item` poi, `tabPurchase Order` po
					where poi.sales_order_item = %s
						and poi.item_code = %s
						and poi.parent = po.name
						and po.docstatus = 1
						and po.status = 'Delivered'""", (item.name, item.item_code))

				item_delivered_qty = item_delivered_qty[0][0] if item_delivered_qty else 0
				item.db_set("delivered_qty", flt(item_delivered_qty), update_modified=False)

			delivered_qty += item.delivered_qty
			tot_qty += item.qty

		self.db_set("per_delivered", flt(delivered_qty/tot_qty) * 100,
			update_modified=False)

	def set_indicator(self):
		"""Set indicator for portal"""
		if self.per_billed < 100 and self.per_delivered < 100:
			self.indicator_color = "orange"
			self.indicator_title = _("Not Paid and Not Delivered")

		elif self.per_billed == 100 and self.per_delivered < 100:
			self.indicator_color = "orange"
			self.indicator_title = _("Paid and Not Delivered")

		else:
			self.indicator_color = "green"
			self.indicator_title = _("Paid")

	def get_production_order_items(self):
		'''Returns items with BOM that already do not have a linked production order'''
		items = []
		for i in self.packed_items or self.items:
			bom = frappe.get_all('BOM', dict(item=i.item_code, is_active=True),
					order_by='is_default desc')
			bom = bom[0].name if bom else None
			items.append(dict(
				item_code= i.item_code,
				bom = bom,
				warehouse = i.warehouse,
				pending_qty= i.stock_qty - flt(frappe.db.sql('''select sum(qty) from `tabProduction Order`
					where production_item=%s and sales_order=%s''', (i.item_code, self.name))[0][0])
			))

		return items


	def on_recurring(self, reference_doc):
		mcount = month_map[reference_doc.recurring_type]
		self.set("delivery_date", get_next_date(reference_doc.delivery_date, mcount,
						cint(reference_doc.repeat_on_day_of_month)))

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Orders'),
	})

	return list_context

@frappe.whitelist()
def close_or_unclose_sales_orders(names, status):
	if not frappe.has_permission("Sales Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	names = json.loads(names)
	for name in names:
		so = frappe.get_doc("Sales Order", name)
		if so.docstatus == 1:
			if status == "Closed":
				if so.status not in ("Cancelled", "Closed") and (so.per_delivered < 100 or so.per_billed < 100):
					so.update_status(status)
			else:
				if so.status == "Closed":
					so.update_status('Draft')

	frappe.local.message_log = []

@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	def postprocess(source, doc):
		doc.material_request_type = "Purchase"

	def update_item(source, target, source_parent):
		target.project = source_parent.project

	doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Material Request",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Packed Item": {
			"doctype": "Material Request Item",
			"field_map": {
				"parent": "sales_order",
				"stock_uom": "uom"
			},
			"postprocess": update_item
		},
		"Sales Order Item": {
			"doctype": "Material Request Item",
			"field_map": {
				"parent": "sales_order",
				"stock_uom": "uom",
				"stock_qty": "qty"
			},
			"condition": lambda doc: not frappe.db.exists('Product Bundle', doc.item_code),
			"postprocess": update_item
		}
	}, target_doc, postprocess)

	return doc

@frappe.whitelist()
def make_project(source_name, target_doc=None):
	def postprocess(source, doc):
		doc.project_type = "External"
		doc.project_name = source.name

	doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Project",
			"validation": {
				"docstatus": ["=", 1]
			},
			"field_map":{
				"name" : "sales_order",
				"delivery_date" : "expected_end_date",
				"base_grand_total" : "estimated_costing",
			}
		},
		"Sales Order Item": {
			"doctype": "Project Task",
			"field_map": {
				"description": "title",
			},
		}
	}, target_doc, postprocess)

	return doc

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	def set_missing_values(source, target):
		if source.po_no:
			if target.po_no:
				target_po_no = target.po_no.split(", ")
				target_po_no.append(source.po_no)
				target.po_no = ", ".join(list(set(target_po_no))) if len(target_po_no) > 1 else target_po_no[0]
			else:
				target.po_no = source.po_no

		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = flt(source.qty) - flt(source.delivered_qty)

		item = frappe.db.get_value("Item", target.item_code, ["item_group", "selling_cost_center"], as_dict=1)
		target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center") \
			or item.selling_cost_center \
			or frappe.db.get_value("Item Group", item.item_group, "default_cost_center")

	target_doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return target_doc

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
	def postprocess(source, target):
		set_missing_values(source, target)
		#Get the advance paid Journal Entries in Sales Invoice Advance
		target.set_advances()

	def set_missing_values(source, target):
		target.is_pos = 0
		target.ignore_pricing_rule = 1
		target.flags.ignore_permissions = True
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent):
		target.amount = flt(source.amount) - flt(source.billed_amt)
		target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = target.amount / flt(source.rate) if (source.rate and source.billed_amt) else source.qty

		item = frappe.db.get_value("Item", target.item_code, ["item_group", "selling_cost_center"], as_dict=1)
		target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center") \
			or item.selling_cost_center \
			or frappe.db.get_value("Item Group", item.item_group, "default_cost_center")

	doclist = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Sales Invoice",
			"field_map": {
				"party_account_currency": "party_account_currency"
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"name": "so_detail",
				"parent": "sales_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.qty and (doc.base_amount==0 or abs(doc.billed_amt) < abs(doc.amount))
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}, target_doc, postprocess, ignore_permissions=ignore_permissions)

	return doclist

@frappe.whitelist()
def make_maintenance_schedule(source_name, target_doc=None):
	maint_schedule = frappe.db.sql("""select t1.name
		from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2
		where t2.parent=t1.name and t2.sales_order=%s and t1.docstatus=1""", source_name)

	if not maint_schedule:
		doclist = get_mapped_doc("Sales Order", source_name, {
			"Sales Order": {
				"doctype": "Maintenance Schedule",
				"validation": {
					"docstatus": ["=", 1]
				}
			},
			"Sales Order Item": {
				"doctype": "Maintenance Schedule Item",
				"field_map": {
					"parent": "sales_order"
				},
				"add_if_empty": True
			}
		}, target_doc)

		return doclist

@frappe.whitelist()
def make_maintenance_visit(source_name, target_doc=None):
	visit = frappe.db.sql("""select t1.name
		from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
		where t2.parent=t1.name and t2.prevdoc_docname=%s
		and t1.docstatus=1 and t1.completion_status='Fully Completed'""", source_name)

	if not visit:
		doclist = get_mapped_doc("Sales Order", source_name, {
			"Sales Order": {
				"doctype": "Maintenance Visit",
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
		}, target_doc)

		return doclist

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Sales Order", filters)

	data = frappe.db.sql("""select name, customer_name, status, delivery_status, billing_status, delivery_date
		from `tabSales Order`
		where (ifnull(delivery_date, '0000-00-00')!= '0000-00-00') \
				and (delivery_date between %(start)s and %(end)s)
				and docstatus < 2
				{conditions}
		""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})
	return data

@frappe.whitelist()
def make_purchase_order_for_drop_shipment(source_name, for_supplier, target_doc=None):
	def set_missing_values(source, target):
		target.supplier = for_supplier
		target.apply_discount_on = ""
		target.additional_discount_percentage = 0.0
		target.discount_amount = 0.0

		default_price_list = frappe.get_value("Supplier", for_supplier, "default_price_list")
		if default_price_list:
			target.buying_price_list = default_price_list

		if any( item.delivered_by_supplier==1 for item in source.items):
			if source.shipping_address_name:
				target.shipping_address = source.shipping_address_name
				target.shipping_address_display = source.shipping_address
			else:
				target.shipping_address = source.customer_address
				target.shipping_address_display = source.address_display

			target.customer_contact_person = source.contact_person
			target.customer_contact_display = source.contact_display
			target.customer_contact_mobile = source.contact_mobile
			target.customer_contact_email = source.contact_email

		else:
			target.customer = ""
			target.customer_name = ""

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent):
		target.schedule_date = source_parent.delivery_date
		target.qty = flt(source.qty) - flt(source.ordered_qty)
		target.stock_qty = (flt(source.qty) - flt(source.ordered_qty)) * flt(source.conversion_factor)

	doclist = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Purchase Order",
			"field_no_map": [
				"address_display",
				"contact_display",
				"contact_mobile",
				"contact_email",
				"contact_person"
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Purchase Order Item",
			"field_map":  [
				["name", "sales_order_item"],
				["parent", "sales_order"],
				["stock_uom", "stock_uom"],
				["uom", "uom"],
				["conversion_factor", "conversion_factor"],
				["delivery_date", "schedule_date"]
			],
			"field_no_map": [
				"rate",
				"price_list_rate"
			],
			"postprocess": update_item,
			"condition": lambda doc: doc.ordered_qty < doc.qty and doc.supplier == for_supplier
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def get_supplier(doctype, txt, searchfield, start, page_len, filters):
	supp_master_name = frappe.defaults.get_user_default("supp_master_name")
	if supp_master_name == "Supplier Name":
		fields = ["name", "supplier_type"]
	else:
		fields = ["name", "supplier_name", "supplier_type"]
	fields = ", ".join(fields)

	return frappe.db.sql("""select {field} from `tabSupplier`
		where docstatus < 2
			and ({key} like %(txt)s
				or supplier_name like %(txt)s)
			and name in (select supplier from `tabSales Order Item` where parent = %(parent)s)
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, supplier_name), locate(%(_txt)s, supplier_name), 99999),
			name, supplier_name
		limit %(start)s, %(page_len)s """.format(**{
			'field': fields,
			'key': frappe.db.escape(searchfield)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'parent': filters.get('parent')
		})

@frappe.whitelist()
def make_production_orders(items, sales_order, company, project=None):
	'''Make Production Orders against the given Sales Order for the given `items`'''
	items = json.loads(items).get('items')
	out = []

	for i in items:
		production_order = frappe.get_doc(dict(
			doctype='Production Order',
			production_item=i['item_code'],
			bom_no=i['bom'],
			qty=i['pending_qty'],
			company=company,
			sales_order=sales_order,
			project=project,
			fg_warehouse=i['warehouse']
		)).insert()
		production_order.set_production_order_operations()
		production_order.save()
		out.append(production_order)

	return [p.name for p in out]

@frappe.whitelist()
def update_status(status, name):
	so = frappe.get_doc("Sales Order", name)
	so.update_status(status)
