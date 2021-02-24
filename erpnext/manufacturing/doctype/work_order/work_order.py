# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
import math
from frappe import _
from frappe.utils import flt, get_datetime, getdate, date_diff, cint, nowdate, get_link_to_form, time_diff_in_hours
from frappe.model.document import Document
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no, get_bom_items_as_dict, get_bom_item_rate
from dateutil.relativedelta import relativedelta
from erpnext.stock.doctype.item.item import validate_end_of_life, get_item_defaults
from erpnext.manufacturing.doctype.workstation.workstation import WorkstationHolidayError
from erpnext.projects.doctype.timesheet.timesheet import OverlapError
from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import get_mins_between_operations
from erpnext.stock.stock_balance import get_planned_qty, update_bin_qty
from frappe.utils.csvutils import getlink
from erpnext.stock.utils import get_bin, validate_warehouse_company, get_latest_stock_qty
from erpnext.utilities.transaction_base import validate_uom_is_integer
from frappe.model.mapper import get_mapped_doc

class OverProductionError(frappe.ValidationError): pass
class CapacityError(frappe.ValidationError): pass
class StockOverProductionError(frappe.ValidationError): pass
class OperationTooLongError(frappe.ValidationError): pass
class ItemHasVariantError(frappe.ValidationError): pass

from six import string_types

form_grid_templates = {
	"operations": "templates/form_grid/work_order_grid.html"
}

class WorkOrder(Document):
	def onload(self):
		ms = frappe.get_doc("Manufacturing Settings")
		self.set_onload("material_consumption", ms.material_consumption)
		self.set_onload("backflush_raw_materials_based_on", ms.backflush_raw_materials_based_on)
		self.set_onload("overproduction_percentage", ms.overproduction_percentage_for_work_order)

	def validate(self):
		self.validate_production_item()
		if self.bom_no:
			validate_bom_no(self.production_item, self.bom_no)

		self.validate_sales_order()
		self.set_default_warehouse()
		self.validate_warehouse_belongs_to_company()
		self.calculate_operating_cost()
		self.validate_qty()
		self.validate_operation_time()
		self.status = self.get_status()

		validate_uom_is_integer(self, "stock_uom", ["qty", "produced_qty"])

		self.set_required_items(reset_only_qty = len(self.get("required_items")))

	def validate_sales_order(self):
		if self.sales_order:
			self.check_sales_order_on_hold_or_close()
			so = frappe.db.sql("""
				select so.name, so_item.delivery_date, so.project
				from `tabSales Order` so
				inner join `tabSales Order Item` so_item on so_item.parent = so.name
				left join `tabProduct Bundle Item` pk_item on so_item.item_code = pk_item.parent
				where so.name=%s and so.docstatus = 1
					and so.skip_delivery_note  = 0 and (
					so_item.item_code=%s or
					pk_item.item_code=%s )
			""", (self.sales_order, self.production_item, self.production_item), as_dict=1)

			if not so:
				so = frappe.db.sql("""
					select
						so.name, so_item.delivery_date, so.project
					from
						`tabSales Order` so, `tabSales Order Item` so_item, `tabPacked Item` packed_item
					where so.name=%s
						and so.name=so_item.parent
						and so.name=packed_item.parent
						and so.skip_delivery_note = 0
						and so_item.item_code = packed_item.parent_item
						and so.docstatus = 1 and packed_item.item_code=%s
				""", (self.sales_order, self.production_item), as_dict=1)

			if len(so):
				if not self.expected_delivery_date:
					self.expected_delivery_date = so[0].delivery_date

				if so[0].project:
					self.project = so[0].project

				if not self.material_request:
					self.validate_work_order_against_so()
			else:
				frappe.throw(_("Sales Order {0} is not valid").format(self.sales_order))

	def check_sales_order_on_hold_or_close(self):
		status = frappe.db.get_value("Sales Order", self.sales_order, "status")
		if status in ("Closed", "On Hold"):
			frappe.throw(_("Sales Order {0} is {1}").format(self.sales_order, status))

	def set_default_warehouse(self):
		if not self.wip_warehouse:
			self.wip_warehouse = frappe.db.get_single_value("Manufacturing Settings", "default_wip_warehouse")
		if not self.fg_warehouse:
			self.fg_warehouse = frappe.db.get_single_value("Manufacturing Settings", "default_fg_warehouse")

	def validate_warehouse_belongs_to_company(self):
		warehouses = [self.fg_warehouse, self.wip_warehouse]
		for d in self.get("required_items"):
			if d.source_warehouse not in warehouses:
				warehouses.append(d.source_warehouse)

		for wh in warehouses:
			validate_warehouse_company(wh, self.company)

	def calculate_operating_cost(self):
		self.planned_operating_cost, self.actual_operating_cost = 0.0, 0.0
		for d in self.get("operations"):
			d.planned_operating_cost = flt(d.hour_rate) * (flt(d.time_in_mins) / 60.0)
			d.actual_operating_cost = flt(d.hour_rate) * (flt(d.actual_operation_time) / 60.0)

			self.planned_operating_cost += flt(d.planned_operating_cost)
			self.actual_operating_cost += flt(d.actual_operating_cost)

		variable_cost = self.actual_operating_cost if self.actual_operating_cost \
			else self.planned_operating_cost
		self.total_operating_cost = flt(self.additional_operating_cost) + flt(variable_cost)

	def validate_work_order_against_so(self):
		# already ordered qty
		ordered_qty_against_so = frappe.db.sql("""select sum(qty) from `tabWork Order`
			where production_item = %s and sales_order = %s and docstatus < 2 and name != %s""",
			(self.production_item, self.sales_order, self.name))[0][0]

		total_qty = flt(ordered_qty_against_so) + flt(self.qty)

		# get qty from Sales Order Item table
		so_item_qty = frappe.db.sql("""select sum(stock_qty) from `tabSales Order Item`
			where parent = %s and item_code = %s""",
			(self.sales_order, self.production_item))[0][0]
		# get qty from Packing Item table
		dnpi_qty = frappe.db.sql("""select sum(qty) from `tabPacked Item`
			where parent = %s and parenttype = 'Sales Order' and item_code = %s""",
			(self.sales_order, self.production_item))[0][0]
		# total qty in SO
		so_qty = flt(so_item_qty) + flt(dnpi_qty)

		allowance_percentage = flt(frappe.db.get_single_value("Manufacturing Settings",
			"overproduction_percentage_for_sales_order"))

		if total_qty > so_qty + (allowance_percentage/100 * so_qty):
			frappe.throw(_("Cannot produce more Item {0} than Sales Order quantity {1}")
				.format(self.production_item, so_qty), OverProductionError)

	def update_status(self, status=None):
		'''Update status of work order if unknown'''
		if status != "Stopped":
			status = self.get_status(status)

		if status != self.status:
			self.db_set("status", status)

		self.update_required_items()

		return status

	def get_status(self, status=None):
		'''Return the status based on stock entries against this work order'''
		if not status:
			status = self.status

		if self.docstatus==0:
			status = 'Draft'
		elif self.docstatus==1:
			if status != 'Stopped':
				stock_entries = frappe._dict(frappe.db.sql("""select purpose, sum(fg_completed_qty)
					from `tabStock Entry` where work_order=%s and docstatus=1
					group by purpose""", self.name))

				status = "Not Started"
				if stock_entries:
					status = "In Process"
					produced_qty = stock_entries.get("Manufacture")
					if flt(produced_qty) >= flt(self.qty):
						status = "Completed"
		else:
			status = 'Cancelled'

		return status

	def update_work_order_qty(self):
		"""Update **Manufactured Qty** and **Material Transferred for Qty** in Work Order
			based on Stock Entry"""

		allowance_percentage = flt(frappe.db.get_single_value("Manufacturing Settings",
			"overproduction_percentage_for_work_order"))

		for purpose, fieldname in (("Manufacture", "produced_qty"),
			("Material Transfer for Manufacture", "material_transferred_for_manufacturing")):
			if (purpose == 'Material Transfer for Manufacture' and
				self.operations and self.transfer_material_against == 'Job Card'):
				continue

			qty = flt(frappe.db.sql("""select sum(fg_completed_qty)
				from `tabStock Entry` where work_order=%s and docstatus=1
				and purpose=%s""", (self.name, purpose))[0][0])

			completed_qty = self.qty + (allowance_percentage/100 * self.qty)
			if qty > completed_qty:
				frappe.throw(_("{0} ({1}) cannot be greater than planned quantity ({2}) in Work Order {3}").format(\
					self.meta.get_label(fieldname), qty, completed_qty, self.name), StockOverProductionError)

			self.db_set(fieldname, qty)

			from erpnext.selling.doctype.sales_order.sales_order import update_produced_qty_in_so_item

			if self.sales_order and self.sales_order_item:
				update_produced_qty_in_so_item(self.sales_order, self.sales_order_item)

		if self.production_plan:
			self.update_production_plan_status()

	def update_production_plan_status(self):
		production_plan = frappe.get_doc('Production Plan', self.production_plan)
		produced_qty = 0
		if self.production_plan_item:
			total_qty = frappe.get_all("Work Order", fields = "sum(produced_qty) as produced_qty",
				filters = {'docstatus': 1, 'production_plan': self.production_plan,
					'production_plan_item': self.production_plan_item}, as_list=1)

			produced_qty = total_qty[0][0] if total_qty else 0

		production_plan.run_method("update_produced_qty", produced_qty, self.production_plan_item)

	def on_submit(self):
		if not self.wip_warehouse:
			frappe.throw(_("Work-in-Progress Warehouse is required before Submit"))
		if not self.fg_warehouse:
			frappe.throw(_("For Warehouse is required before Submit"))

		self.update_work_order_qty_in_so()
		self.update_reserved_qty_for_production()
		self.update_completed_qty_in_material_request()
		self.update_planned_qty()
		self.update_ordered_qty()
		self.create_job_card()

	def on_cancel(self):
		self.validate_cancel()

		frappe.db.set(self,'status', 'Cancelled')
		self.update_work_order_qty_in_so()
		self.delete_job_card()
		self.update_completed_qty_in_material_request()
		self.update_planned_qty()
		self.update_ordered_qty()
		self.update_reserved_qty_for_production()

	def create_job_card(self):
		manufacturing_settings_doc = frappe.get_doc("Manufacturing Settings")

		enable_capacity_planning = not cint(manufacturing_settings_doc.disable_capacity_planning)
		plan_days = cint(manufacturing_settings_doc.capacity_planning_for_days) or 30

		for i, row in enumerate(self.operations):
			self.set_operation_start_end_time(i, row)

			if not row.workstation:
				frappe.throw(_("Row {0}: select the workstation against the operation {1}")
					.format(row.idx, row.operation))

			original_start_time = row.planned_start_time
			job_card_doc = create_job_card(self, row,
				enable_capacity_planning=enable_capacity_planning, auto_create=True)

			if enable_capacity_planning and job_card_doc:
				row.planned_start_time = job_card_doc.time_logs[-1].from_time
				row.planned_end_time = job_card_doc.time_logs[-1].to_time

				if date_diff(row.planned_start_time, original_start_time) > plan_days:
					frappe.message_log.pop()
					frappe.throw(_("Unable to find the time slot in the next {0} days for the operation {1}.")
						.format(plan_days, row.operation), CapacityError)

				row.db_update()

		planned_end_date = self.operations and self.operations[-1].planned_end_time
		if planned_end_date:
			self.db_set("planned_end_date", planned_end_date)

	def set_operation_start_end_time(self, idx, row):
		"""Set start and end time for given operation. If first operation, set start as
		`planned_start_date`, else add time diff to end time of earlier operation."""
		if idx==0:
			# first operation at planned_start date
			row.planned_start_time = self.planned_start_date
		else:
			row.planned_start_time = get_datetime(self.operations[idx-1].planned_end_time)\
				+ get_mins_between_operations()

		row.planned_end_time = get_datetime(row.planned_start_time) + relativedelta(minutes = row.time_in_mins)

		if row.planned_start_time == row.planned_end_time:
			frappe.throw(_("Capacity Planning Error, planned start time can not be same as end time"))

	def validate_cancel(self):
		if self.status == "Stopped":
			frappe.throw(_("Stopped Work Order cannot be cancelled, Unstop it first to cancel"))

		# Check whether any stock entry exists against this Work Order
		stock_entry = frappe.db.sql("""select name from `tabStock Entry`
			where work_order = %s and docstatus = 1""", self.name)
		if stock_entry:
			frappe.throw(_("Cannot cancel because submitted Stock Entry {0} exists").format(frappe.utils.get_link_to_form('Stock Entry', stock_entry[0][0])))

	def update_planned_qty(self):
		update_bin_qty(self.production_item, self.fg_warehouse, {
			"planned_qty": get_planned_qty(self.production_item, self.fg_warehouse)
		})

		if self.material_request:
			mr_obj = frappe.get_doc("Material Request", self.material_request)
			mr_obj.update_requested_qty([self.material_request_item])

	def update_ordered_qty(self):
		if self.production_plan and self.production_plan_item:
			qty = self.qty if self.docstatus == 1 else 0
			frappe.db.set_value('Production Plan Item',
				self.production_plan_item, 'ordered_qty', qty)

			doc = frappe.get_doc('Production Plan', self.production_plan)
			doc.set_status()
			doc.db_set('status', doc.status)

	def update_work_order_qty_in_so(self):
		if not self.sales_order and not self.sales_order_item:
			return

		total_bundle_qty = 1
		if self.product_bundle_item:
			total_bundle_qty = frappe.db.sql(""" select sum(qty) from
				`tabProduct Bundle Item` where parent = %s""", (frappe.db.escape(self.product_bundle_item)))[0][0]

			if not total_bundle_qty:
				# product bundle is 0 (product bundle allows 0 qty for items)
				total_bundle_qty = 1

		cond = "product_bundle_item = %s" if self.product_bundle_item else "production_item = %s"

		qty = frappe.db.sql(""" select sum(qty) from
			`tabWork Order` where sales_order = %s and docstatus = 1 and {0}
			""".format(cond), (self.sales_order, (self.product_bundle_item or self.production_item)), as_list=1)

		work_order_qty = qty[0][0] if qty and qty[0][0] else 0
		frappe.db.set_value('Sales Order Item',
			self.sales_order_item, 'work_order_qty', flt(work_order_qty/total_bundle_qty, 2))

	def update_completed_qty_in_material_request(self):
		if self.material_request:
			frappe.get_doc("Material Request", self.material_request).update_completed_qty([self.material_request_item])

	def set_work_order_operations(self):
		"""Fetch operations from BOM and set in 'Work Order'"""
		self.set('operations', [])

		if not self.bom_no:
			return

		if self.use_multi_level_bom:
			bom_list = frappe.get_doc("BOM", self.bom_no).traverse_tree()
		else:
			bom_list = [self.bom_no]

		operations = frappe.db.sql("""
			select
				operation, description, workstation, idx,
				base_hour_rate as hour_rate, time_in_mins,
				"Pending" as status, parent as bom, batch_size, sequence_id
			from
				`tabBOM Operation`
			where
				 parent in (%s) order by idx
		"""	% ", ".join(["%s"]*len(bom_list)), tuple(bom_list), as_dict=1)

		self.set('operations', operations)

		if self.use_multi_level_bom and self.get('operations') and self.get('items'):
			raw_material_operations = [d.operation for d in self.get('items')]
			operations = [d.operation for d in self.get('operations')]

			for operation in raw_material_operations:
				if operation not in operations:
					self.append('operations', {
						'operation': operation
					})

		self.calculate_time()

	def calculate_time(self):
		bom_qty = frappe.db.get_value("BOM", self.bom_no, "quantity")

		for d in self.get("operations"):
			d.time_in_mins = flt(d.time_in_mins) / flt(bom_qty) * (flt(self.qty) / flt(d.batch_size))

		self.calculate_operating_cost()

	def get_holidays(self, workstation):
		holiday_list = frappe.db.get_value("Workstation", workstation, "holiday_list")

		holidays = {}

		if holiday_list not in holidays:
			holiday_list_days = [getdate(d[0]) for d in frappe.get_all("Holiday", fields=["holiday_date"],
				filters={"parent": holiday_list}, order_by="holiday_date", limit_page_length=0, as_list=1)]

			holidays[holiday_list] = holiday_list_days

		return holidays[holiday_list]

	def update_operation_status(self):
		allowance_percentage = flt(frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order"))
		max_allowed_qty_for_wo = flt(self.qty) + (allowance_percentage/100 * flt(self.qty))

		for d in self.get("operations"):
			if not d.completed_qty:
				d.status = "Pending"
			elif flt(d.completed_qty) < flt(self.qty):
				d.status = "Work in Progress"
			elif flt(d.completed_qty) == flt(self.qty):
				d.status = "Completed"
			elif flt(d.completed_qty) <= max_allowed_qty_for_wo:
				d.status = "Completed"
			else:
				frappe.throw(_("Completed Qty cannot be greater than 'Qty to Manufacture'"))

	def set_actual_dates(self):
		if self.get("operations"):
			actual_start_dates = [d.actual_start_time for d in self.get("operations") if d.actual_start_time]
			if actual_start_dates:
				self.actual_start_date = min(actual_start_dates)

			actual_end_dates = [d.actual_end_time for d in self.get("operations") if d.actual_end_time]
			if actual_end_dates:
				self.actual_end_date = max(actual_end_dates)
		else:
			data = frappe.get_all("Stock Entry",
				fields = ["timestamp(posting_date, posting_time) as posting_datetime"],
				filters = {
					"work_order": self.name,
					"purpose": ("in", ["Material Transfer for Manufacture", "Manufacture"])
				}
			)

			if data and len(data):
				dates = [d.posting_datetime for d in data]
				self.db_set('actual_start_date', min(dates))

				if self.status == "Completed":
					self.db_set('actual_end_date', max(dates))

		self.set_lead_time()

	def set_lead_time(self):
		if self.actual_start_date and self.actual_end_date:
			self.lead_time = flt(time_diff_in_hours(self.actual_end_date, self.actual_start_date) * 60)

	def delete_job_card(self):
		for d in frappe.get_all("Job Card", ["name"], {"work_order": self.name}):
			frappe.delete_doc("Job Card", d.name)

	def validate_production_item(self):
		if frappe.db.get_value("Item", self.production_item, "has_variants"):
			frappe.throw(_("Work Order cannot be raised against a Item Template"), ItemHasVariantError)

		if self.production_item:
			validate_end_of_life(self.production_item)

	def validate_qty(self):
		if not self.qty > 0:
			frappe.throw(_("Quantity to Manufacture must be greater than 0."))

	def validate_operation_time(self):
		for d in self.operations:
			if not d.time_in_mins > 0:
				frappe.throw(_("Operation Time must be greater than 0 for Operation {0}").format(d.operation))

	def update_required_items(self):
		'''
		update bin reserved_qty_for_production
		called from Stock Entry for production, after submit, cancel
		'''
		# calculate consumed qty based on submitted stock entries
		self.update_consumed_qty_for_required_items()

		if self.docstatus==1:
			# calculate transferred qty based on submitted stock entries
			self.update_transaferred_qty_for_required_items()

			# update in bin
			self.update_reserved_qty_for_production()

	def update_reserved_qty_for_production(self, items=None):
		'''update reserved_qty_for_production in bins'''
		for d in self.required_items:
			if d.source_warehouse:
				stock_bin = get_bin(d.item_code, d.source_warehouse)
				stock_bin.update_reserved_qty_for_production()

	def get_items_and_operations_from_bom(self):
		self.set_required_items()
		self.set_work_order_operations()

		return check_if_scrap_warehouse_mandatory(self.bom_no)

	def set_available_qty(self):
		for d in self.get("required_items"):
			if d.source_warehouse:
				d.available_qty_at_source_warehouse = get_latest_stock_qty(d.item_code, d.source_warehouse)

			if self.wip_warehouse:
				d.available_qty_at_wip_warehouse = get_latest_stock_qty(d.item_code, self.wip_warehouse)

	def set_required_items(self, reset_only_qty=False):
		'''set required_items for production to keep track of reserved qty'''
		if not reset_only_qty:
			self.required_items = []

		if self.bom_no and self.qty:
			item_dict = get_bom_items_as_dict(self.bom_no, self.company, qty=self.qty,
				fetch_exploded = self.use_multi_level_bom)

			if reset_only_qty:
				for d in self.get("required_items"):
					if item_dict.get(d.item_code):
						d.required_qty = item_dict.get(d.item_code).get("qty")
			else:
				# Attribute a big number (999) to idx for sorting putpose in case idx is NULL
				# For instance in BOM Explosion Item child table, the items coming from sub assembly items
				for item in sorted(item_dict.values(), key=lambda d: d['idx'] or 9999):
					self.append('required_items', {
						'rate': item.rate,
						'amount': item.amount,
						'operation': item.operation,
						'item_code': item.item_code,
						'item_name': item.item_name,
						'description': item.description,
						'allow_alternative_item': item.allow_alternative_item,
						'required_qty': item.qty,
						'source_warehouse': item.source_warehouse or item.default_warehouse,
						'include_item_in_manufacturing': item.include_item_in_manufacturing
					})

					if not self.project:
						self.project = item.get("project")

			self.set_available_qty()

	def update_transaferred_qty_for_required_items(self):
		'''update transferred qty from submitted stock entries for that item against
			the work order'''

		for d in self.required_items:
			transferred_qty = frappe.db.sql('''select sum(qty)
				from `tabStock Entry` entry, `tabStock Entry Detail` detail
				where
					entry.work_order = %(name)s
					and entry.purpose = "Material Transfer for Manufacture"
					and entry.docstatus = 1
					and detail.parent = entry.name
					and (detail.item_code = %(item)s or detail.original_item = %(item)s)''', {
						'name': self.name,
						'item': d.item_code
					})[0][0]

			d.db_set('transferred_qty', flt(transferred_qty), update_modified = False)

	def update_consumed_qty_for_required_items(self):
		'''
			Update consumed qty from submitted stock entries
			against a work order for each stock item
		'''

		for item in self.required_items:
			consumed_qty = frappe.db.sql('''
				SELECT
					SUM(qty)
				FROM
					`tabStock Entry` entry,
					`tabStock Entry Detail` detail
				WHERE
					entry.work_order = %(name)s
						AND (entry.purpose = "Material Consumption for Manufacture"
							OR entry.purpose = "Manufacture")
						AND entry.docstatus = 1
						AND detail.parent = entry.name
						AND detail.s_warehouse IS NOT null
						AND (detail.item_code = %(item)s
							OR detail.original_item = %(item)s)
				''', {
					'name': self.name,
					'item': item.item_code
				})[0][0]

			item.db_set('consumed_qty', flt(consumed_qty), update_modified=False)

	def make_bom(self):
		data = frappe.db.sql(""" select sed.item_code, sed.qty, sed.s_warehouse
			from `tabStock Entry Detail` sed, `tabStock Entry` se
			where se.name = sed.parent and se.purpose = 'Manufacture'
			and (sed.t_warehouse is null or sed.t_warehouse = '') and se.docstatus = 1
			and se.work_order = %s""", (self.name), as_dict=1)

		bom = frappe.new_doc("BOM")
		bom.item = self.production_item
		bom.conversion_rate = 1

		for d in data:
			bom.append('items', {
				'item_code': d.item_code,
				'qty': d.qty,
				'source_warehouse': d.s_warehouse
			})

		if self.operations:
			bom.set('operations', self.operations)
			bom.with_operations = 1

		bom.set_bom_material_details()
		return bom

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_bom_operations(doctype, txt, searchfield, start, page_len, filters):
	if txt:
		filters['operation'] = ('like', '%%%s%%' % txt)

	return frappe.get_all('BOM Operation',
		filters = filters, fields = ['operation'], as_list=1)

@frappe.whitelist()
def get_item_details(item, project = None, skip_bom_info=False):
	res = frappe.db.sql("""
		select stock_uom, description, item_name, allow_alternative_item,
			include_item_in_manufacturing
		from `tabItem`
		where disabled=0
			and (end_of_life is null or end_of_life='0000-00-00' or end_of_life > %s)
			and name=%s
	""", (nowdate(), item), as_dict=1)

	if not res:
		return {}

	res = res[0]
	if skip_bom_info: return res

	filters = {"item": item, "is_default": 1}

	if project:
		filters = {"item": item, "project": project}

	res["bom_no"] = frappe.db.get_value("BOM", filters = filters)

	if not res["bom_no"]:
		variant_of= frappe.db.get_value("Item", item, "variant_of")

		if variant_of:
			res["bom_no"] = frappe.db.get_value("BOM", filters={"item": variant_of, "is_default": 1})

	if not res["bom_no"]:
		if project:
			res = get_item_details(item)
			frappe.msgprint(_("Default BOM not found for Item {0} and Project {1}").format(item, project), alert=1)
		else:
			frappe.throw(_("Default BOM for {0} not found").format(item))

	bom_data = frappe.db.get_value('BOM', res['bom_no'],
		['project', 'allow_alternative_item', 'transfer_material_against', 'item_name'], as_dict=1)

	res['project'] = project or bom_data.pop("project")
	res.update(bom_data)
	res.update(check_if_scrap_warehouse_mandatory(res["bom_no"]))

	return res

@frappe.whitelist()
def make_work_order(bom_no, item, qty=0, project=None, variant_items=None):
	if not frappe.has_permission("Work Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	item_details = get_item_details(item, project)

	wo_doc = frappe.new_doc("Work Order")
	wo_doc.production_item = item
	wo_doc.update(item_details)
	wo_doc.bom_no = bom_no

	if flt(qty) > 0:
		wo_doc.qty = flt(qty)
		wo_doc.get_items_and_operations_from_bom()

	if variant_items:
		add_variant_item(variant_items, wo_doc, bom_no, "required_items")

	return wo_doc

def add_variant_item(variant_items, wo_doc, bom_no, table_name="items"):
	if isinstance(variant_items, string_types):
		variant_items = json.loads(variant_items)

	for item in variant_items:
		args = frappe._dict({
			"item_code": item.get("varint_item_code"),
			"required_qty": item.get("qty"),
			"qty": item.get("qty"), # for bom
			"source_warehouse": item.get("source_warehouse"),
			"operation": item.get("operation")
		})

		bom_doc = frappe.get_cached_doc("BOM", bom_no)
		item_data = get_item_details(args.item_code, skip_bom_info=True)
		args.update(item_data)

		args["rate"] = get_bom_item_rate({
			"company": wo_doc.company,
			"item_code": args.get("item_code"),
			"qty": args.get("required_qty"),
			"uom": args.get("stock_uom"),
			"stock_uom": args.get("stock_uom"),
			"conversion_factor": 1
		}, bom_doc)

		if not args.source_warehouse:
			args["source_warehouse"] = get_item_defaults(item.get("varint_item_code"),
				wo_doc.company).default_warehouse

		args["amount"] = flt(args.get("required_qty")) * flt(args.get("rate"))
		args["uom"] = item_data.stock_uom
		wo_doc.append(table_name, args)

@frappe.whitelist()
def check_if_scrap_warehouse_mandatory(bom_no):
	res = {"set_scrap_wh_mandatory": False }
	if bom_no:
		bom = frappe.get_doc("BOM", bom_no)

		if len(bom.scrap_items) > 0:
			res["set_scrap_wh_mandatory"] = True

	return res

@frappe.whitelist()
def set_work_order_ops(name):
	po = frappe.get_doc('Work Order', name)
	po.set_work_order_operations()
	po.save()

@frappe.whitelist()
def make_stock_entry(work_order_id, purpose, qty=None):
	work_order = frappe.get_doc("Work Order", work_order_id)
	if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
		wip_warehouse = work_order.wip_warehouse
	else:
		wip_warehouse = None

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = purpose
	stock_entry.work_order = work_order_id
	stock_entry.company = work_order.company
	stock_entry.from_bom = 1
	stock_entry.bom_no = work_order.bom_no
	stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
	stock_entry.fg_completed_qty = qty or (flt(work_order.qty) - flt(work_order.produced_qty))
	if work_order.bom_no:
		stock_entry.inspection_required = frappe.db.get_value('BOM',
			work_order.bom_no, 'inspection_required')

	if purpose=="Material Transfer for Manufacture":
		stock_entry.to_warehouse = wip_warehouse
		stock_entry.project = work_order.project
	else:
		stock_entry.from_warehouse = wip_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.project = work_order.project

	stock_entry.set_stock_entry_type()
	stock_entry.get_items()
	return stock_entry.as_dict()

@frappe.whitelist()
def get_default_warehouse():
	doc = frappe.get_cached_doc("Manufacturing Settings")

	return {
		"wip_warehouse": doc.default_wip_warehouse,
		"fg_warehouse": doc.default_fg_warehouse,
		"scrap_warehouse": doc.default_scrap_warehouse
	}

@frappe.whitelist()
def stop_unstop(work_order, status):
	""" Called from client side on Stop/Unstop event"""

	if not frappe.has_permission("Work Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	pro_order = frappe.get_doc("Work Order", work_order)
	pro_order.update_status(status)
	pro_order.update_planned_qty()
	frappe.msgprint(_("Work Order has been {0}").format(status))
	pro_order.notify_update()

	return pro_order.status

@frappe.whitelist()
def query_sales_order(production_item):
	out = frappe.db.sql_list("""
		select distinct so.name from `tabSales Order` so, `tabSales Order Item` so_item
		where so_item.parent=so.name and so_item.item_code=%s and so.docstatus=1
	union
		select distinct so.name from `tabSales Order` so, `tabPacked Item` pi_item
		where pi_item.parent=so.name and pi_item.item_code=%s and so.docstatus=1
	""", (production_item, production_item))

	return out

@frappe.whitelist()
def make_job_card(work_order, operations):
	if isinstance(operations, string_types):
		operations = json.loads(operations)

	work_order = frappe.get_doc('Work Order', work_order)
	for row in operations:
		validate_operation_data(row)
		create_job_card(work_order, row, row.get("qty"), auto_create=True)

def validate_operation_data(row):
	if row.get("qty") <= 0:
		frappe.throw(_("Quantity to Manufacture can not be zero for the operation {0}")
			.format(
				frappe.bold(row.get("operation"))
			)
		)

	if row.get("qty") > row.get("pending_qty"):
		frappe.throw(_("For operation {0}: Quantity ({1}) can not be greter than pending quantity({2})")
			.format(
				frappe.bold(row.get("operation")),
				frappe.bold(row.get("qty")),
				frappe.bold(row.get("pending_qty"))
			)
		)

def create_job_card(work_order, row, qty=0, enable_capacity_planning=False, auto_create=False):
	doc = frappe.new_doc("Job Card")
	doc.update({
		'work_order': work_order.name,
		'operation': row.get("operation"),
		'workstation': row.get("workstation"),
		'posting_date': nowdate(),
		'for_quantity': qty or work_order.get('qty', 0),
		'operation_id': row.get("name"),
		'bom_no': work_order.bom_no,
		'project': work_order.project,
		'company': work_order.company,
		'sequence_id': row.get("sequence_id"),
		'wip_warehouse': work_order.wip_warehouse
	})

	if work_order.transfer_material_against == 'Job Card' and not work_order.skip_transfer:
		doc.get_required_items()

	if auto_create:
		doc.flags.ignore_mandatory = True
		if enable_capacity_planning:
			doc.schedule_time_logs(row)

		doc.insert()
		frappe.msgprint(_("Job card {0} created").format(get_link_to_form("Job Card", doc.name)))

	return doc

def get_work_order_operation_data(work_order, operation, workstation):
	for d in work_order.operations:
		if d.operation == operation and d.workstation == workstation:
			return d

@frappe.whitelist()
def create_pick_list(source_name, target_doc=None, for_qty=None):
	for_qty = for_qty or json.loads(target_doc).get('for_qty')
	max_finished_goods_qty = frappe.db.get_value('Work Order', source_name, 'qty')
	def update_item_quantity(source, target, source_parent):
		pending_to_issue = flt(source.required_qty) - flt(source.transferred_qty)
		desire_to_transfer = flt(source.required_qty) / max_finished_goods_qty * flt(for_qty)

		qty = 0
		if desire_to_transfer <= pending_to_issue:
			qty = desire_to_transfer
		elif pending_to_issue > 0:
			qty = pending_to_issue

		if qty:
			target.qty = qty
			target.stock_qty = qty
			target.uom = frappe.get_value('Item', source.item_code, 'stock_uom')
			target.stock_uom = target.uom
			target.conversion_factor = 1
		else:
			target.delete()

	doc = get_mapped_doc('Work Order', source_name, {
		'Work Order': {
			'doctype': 'Pick List',
			'validation': {
				'docstatus': ['=', 1]
			}
		},
		'Work Order Item': {
			'doctype': 'Pick List Item',
			'postprocess': update_item_quantity,
			'condition': lambda doc: abs(doc.transferred_qty) < abs(doc.required_qty)
		},
	}, target_doc)

	doc.for_qty = for_qty

	doc.set_item_locations()

	return doc
