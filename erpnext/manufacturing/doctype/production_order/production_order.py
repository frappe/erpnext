# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
from six import text_type
from frappe import _
from frappe.utils import flt, get_datetime, getdate, date_diff, cint, nowdate
from frappe.model.document import Document
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no, get_bom_items_as_dict
from dateutil.relativedelta import relativedelta
from erpnext.stock.doctype.item.item import validate_end_of_life
from erpnext.manufacturing.doctype.workstation.workstation import WorkstationHolidayError
from erpnext.projects.doctype.timesheet.timesheet import OverlapError
from erpnext.stock.doctype.stock_entry.stock_entry import get_additional_costs
from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import get_mins_between_operations
from erpnext.stock.stock_balance import get_planned_qty, update_bin_qty
from frappe.utils.csvutils import getlink
from erpnext.stock.utils import get_bin, validate_warehouse_company, get_latest_stock_qty
from erpnext.utilities.transaction_base import validate_uom_is_integer

class OverProductionError(frappe.ValidationError): pass
class StockOverProductionError(frappe.ValidationError): pass
class OperationTooLongError(frappe.ValidationError): pass
class ItemHasVariantError(frappe.ValidationError): pass

form_grid_templates = {
	"operations": "templates/form_grid/production_order_grid.html"
}

class ProductionOrder(Document):
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
			so = frappe.db.sql("""
				select so.name, so_item.delivery_date, so.project
				from `tabSales Order` so
				inner join `tabSales Order Item` so_item on so_item.parent = so.name
				left join `tabProduct Bundle Item` pk_item on so_item.item_code = pk_item.parent
				where so.name=%s and so.docstatus = 1 and (
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
						and so_item.item_code = packed_item.parent_item
						and so.docstatus = 1 and packed_item.item_code=%s
				""", (self.sales_order, self.production_item), as_dict=1)

			if len(so):
				if not self.expected_delivery_date:
					self.expected_delivery_date = so[0].delivery_date

				if so[0].project:
					self.project = so[0].project

				if not self.material_request:
					self.validate_production_order_against_so()
			else:
				frappe.throw(_("Sales Order {0} is not valid").format(self.sales_order))

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

	def validate_production_order_against_so(self):
		# already ordered qty
		ordered_qty_against_so = frappe.db.sql("""select sum(qty) from `tabProduction Order`
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
			"over_production_allowance_percentage"))

		if total_qty > so_qty + (allowance_percentage/100 * so_qty):
			frappe.throw(_("Cannot produce more Item {0} than Sales Order quantity {1}")
				.format(self.production_item, so_qty), OverProductionError)

	def update_status(self, status=None):
		'''Update status of production order if unknown'''
		if status != "Stopped":
			status = self.get_status(status)

		if status != self.status:
			self.db_set("status", status)

		self.update_required_items()

		return status

	def get_status(self, status=None):
		'''Return the status based on stock entries against this production order'''
		if not status:
			status = self.status

		if self.docstatus==0:
			status = 'Draft'
		elif self.docstatus==1:
			if status != 'Stopped':
				stock_entries = frappe._dict(frappe.db.sql("""select purpose, sum(fg_completed_qty)
					from `tabStock Entry` where production_order=%s and docstatus=1
					group by purpose""", self.name))

				status = "Not Started"
				if stock_entries:
					status = "In Process"
					produced_qty = stock_entries.get("Manufacture")
					if flt(produced_qty) == flt(self.qty):
						status = "Completed"
		else:
			status = 'Cancelled'

		return status

	def update_production_order_qty(self):
		"""Update **Manufactured Qty** and **Material Transferred for Qty** in Production Order
			based on Stock Entry"""

		for purpose, fieldname in (("Manufacture", "produced_qty"),
			("Material Transfer for Manufacture", "material_transferred_for_manufacturing")):
			qty = flt(frappe.db.sql("""select sum(fg_completed_qty)
				from `tabStock Entry` where production_order=%s and docstatus=1
				and purpose=%s""", (self.name, purpose))[0][0])

			if qty > self.qty:
				frappe.throw(_("{0} ({1}) cannot be greater than planned quanitity ({2}) in Production Order {3}").format(\
					self.meta.get_label(fieldname), qty, self.qty, self.name), StockOverProductionError)

			self.db_set(fieldname, qty)

	def before_submit(self):
		self.make_time_logs()

	def on_submit(self):
		if not self.wip_warehouse:
			frappe.throw(_("Work-in-Progress Warehouse is required before Submit"))
		if not self.fg_warehouse:
			frappe.throw(_("For Warehouse is required before Submit"))

		self.update_reserved_qty_for_production()
		self.update_completed_qty_in_material_request()
		self.update_planned_qty()

	def on_cancel(self):
		self.validate_cancel()

		frappe.db.set(self,'status', 'Cancelled')
		self.delete_timesheet()
		self.update_completed_qty_in_material_request()
		self.update_planned_qty()
		self.update_reserved_qty_for_production()

	def validate_cancel(self):
		if self.status == "Stopped":
			frappe.throw(_("Stopped Production Order cannot be cancelled, Unstop it first to cancel"))

		# Check whether any stock entry exists against this Production Order
		stock_entry = frappe.db.sql("""select name from `tabStock Entry`
			where production_order = %s and docstatus = 1""", self.name)
		if stock_entry:
			frappe.throw(_("Cannot cancel because submitted Stock Entry {0} exists").format(stock_entry[0][0]))

	def update_planned_qty(self):
		update_bin_qty(self.production_item, self.fg_warehouse, {
			"planned_qty": get_planned_qty(self.production_item, self.fg_warehouse)
		})

		if self.material_request:
			mr_obj = frappe.get_doc("Material Request", self.material_request)
			mr_obj.update_requested_qty([self.material_request_item])

	def update_completed_qty_in_material_request(self):
		if self.material_request:
			frappe.get_doc("Material Request", self.material_request).update_completed_qty([self.material_request_item])

	def set_production_order_operations(self):
		"""Fetch operations from BOM and set in 'Production Order'"""
		self.set('operations', [])

		if not self.bom_no \
			or cint(frappe.db.get_single_value("Manufacturing Settings", "disable_capacity_planning")):
				return

		if self.use_multi_level_bom:
			bom_list = frappe.get_doc("BOM", self.bom_no).traverse_tree()
		else:
			bom_list = [self.bom_no]

		operations = frappe.db.sql("""
			select
				operation, description, workstation, idx,
				base_hour_rate as hour_rate, time_in_mins,
				"Pending" as status, parent as bom
			from
				`tabBOM Operation`
			where
				 parent in (%s) order by idx
		"""	% ", ".join(["%s"]*len(bom_list)), tuple(bom_list), as_dict=1)

		self.set('operations', operations)
		self.calculate_time()

	def calculate_time(self):
		bom_qty = frappe.db.get_value("BOM", self.bom_no, "quantity")

		for d in self.get("operations"):
			d.time_in_mins = flt(d.time_in_mins) / flt(bom_qty) * flt(self.qty)

		self.calculate_operating_cost()

	def get_holidays(self, workstation):
		holiday_list = frappe.db.get_value("Workstation", workstation, "holiday_list")

		holidays = {}

		if holiday_list not in holidays:
			holiday_list_days = [getdate(d[0]) for d in frappe.get_all("Holiday", fields=["holiday_date"],
				filters={"parent": holiday_list}, order_by="holiday_date", limit_page_length=0, as_list=1)]

			holidays[holiday_list] = holiday_list_days

		return holidays[holiday_list]

	def make_time_logs(self, open_new=False):
		"""Capacity Planning. Plan time logs based on earliest availablity of workstation after
			Planned Start Date. Time logs will be created and remain in Draft mode and must be submitted
			before manufacturing entry can be made."""

		if not self.operations:
			return

		timesheets = []
		plan_days = frappe.db.get_single_value("Manufacturing Settings", "capacity_planning_for_days") or 30

		timesheet = make_timesheet(self.name, self.company)
		timesheet.set('time_logs', [])

		for i, d in enumerate(self.operations):

			if d.status != 'Completed':
				self.set_start_end_time_for_workstation(d, i)

				args = self.get_operations_data(d)

				add_timesheet_detail(timesheet, args)
				original_start_time = d.planned_start_time

				# validate operating hours if workstation [not mandatory] is specified
				try:
					timesheet.validate_time_logs()
				except OverlapError:
					if frappe.message_log: frappe.message_log.pop()
					timesheet.schedule_for_production_order(d.idx)
				except WorkstationHolidayError:
					if frappe.message_log: frappe.message_log.pop()
					timesheet.schedule_for_production_order(d.idx)

				from_time, to_time = self.get_start_end_time(timesheet, d.name)

				if date_diff(from_time, original_start_time) > cint(plan_days):
					frappe.throw(_("Unable to find Time Slot in the next {0} days for Operation {1}").format(plan_days, d.operation))
					break

				d.planned_start_time = from_time
				d.planned_end_time = to_time
				d.db_update()

		if timesheet and open_new:
			return timesheet

		if timesheet and timesheet.get("time_logs"):
			timesheet.save()
			timesheets.append(getlink("Timesheet", timesheet.name))

		self.planned_end_date = self.operations[-1].planned_end_time
		if timesheets:
			frappe.local.message_log = []
			frappe.msgprint(_("Timesheet created:") + "\n" + "\n".join(timesheets))

	def get_operations_data(self, data):
		return {
			'from_time': get_datetime(data.planned_start_time),
			'hours': data.time_in_mins / 60.0,
			'to_time': get_datetime(data.planned_end_time),
			'project': self.project,
			'operation': data.operation,
			'operation_id': data.name,
			'workstation': data.workstation,
			'completed_qty': flt(self.qty) - flt(data.completed_qty)
		}

	def set_start_end_time_for_workstation(self, data, index):
		"""Set start and end time for given operation. If first operation, set start as
		`planned_start_date`, else add time diff to end time of earlier operation."""

		if index == 0:
			data.planned_start_time = self.planned_start_date
		else:
			data.planned_start_time = get_datetime(self.operations[index-1].planned_end_time)\
								+ get_mins_between_operations()

		data.planned_end_time = get_datetime(data.planned_start_time) + relativedelta(minutes = data.time_in_mins)

		if data.planned_start_time == data.planned_end_time:
			frappe.throw(_("Capacity Planning Error"))

	def get_start_end_time(self, timesheet, operation_id):
		for data in timesheet.time_logs:
			if data.operation_id == operation_id:
				return data.from_time, data.to_time

	def check_operation_fits_in_working_hours(self, d):
		"""Raises expection if operation is longer than working hours in the given workstation."""
		from erpnext.manufacturing.doctype.workstation.workstation import check_if_within_operating_hours
		check_if_within_operating_hours(d.workstation, d.operation, d.planned_start_time, d.planned_end_time)

	def update_operation_status(self):
		for d in self.get("operations"):
			if not d.completed_qty:
				d.status = "Pending"
			elif flt(d.completed_qty) < flt(self.qty):
				d.status = "Work in Progress"
			elif flt(d.completed_qty) == flt(self.qty):
				d.status = "Completed"
			else:
				frappe.throw(_("Completed Qty can not be greater than 'Qty to Manufacture'"))

	def set_actual_dates(self):
		self.actual_start_date = None
		self.actual_end_date = None
		if self.get("operations"):
			actual_start_dates = [d.actual_start_time for d in self.get("operations") if d.actual_start_time]
			if actual_start_dates:
				self.actual_start_date = min(actual_start_dates)

			actual_end_dates = [d.actual_end_time for d in self.get("operations") if d.actual_end_time]
			if actual_end_dates:
				self.actual_end_date = max(actual_end_dates)

	def delete_timesheet(self):
		for timesheet in frappe.get_all("Timesheet", ["name"], {"production_order": self.name}):
			frappe.delete_doc("Timesheet", timesheet.name)

	def validate_production_item(self):
		if frappe.db.get_value("Item", self.production_item, "has_variants"):
			frappe.throw(_("Production Order cannot be raised against a Item Template"), ItemHasVariantError)

		if self.production_item:
			validate_end_of_life(self.production_item)

	def validate_qty(self):
		if not self.qty > 0:
			frappe.throw(_("Quantity to Manufacture must be greater than 0."))

	def validate_operation_time(self):
		for d in self.operations:
			if not d.time_in_mins > 0:
				frappe.throw(_("Operation Time must be greater than 0 for Operation {0}".format(d.operation)))

	def update_required_items(self):
		'''
		update bin reserved_qty_for_production
		called from Stock Entry for production, after submit, cancel
		'''
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
		self.set_production_order_operations()

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
				for item in sorted(item_dict.values(), key=lambda d: d['idx']):
					self.append('required_items', {
						'item_code': item.item_code,
						'item_name': item.item_name,
						'description': item.description,
						'required_qty': item.qty,
						'source_warehouse': item.source_warehouse or item.default_warehouse
					})

			self.set_available_qty()

	def update_transaferred_qty_for_required_items(self):
		'''update transferred qty from submitted stock entries for that item against
			the production order'''

		for d in self.required_items:
			transferred_qty = frappe.db.sql('''select sum(qty)
				from `tabStock Entry` entry, `tabStock Entry Detail` detail
				where
					entry.production_order = %s
					and entry.purpose = "Material Transfer for Manufacture"
					and entry.docstatus = 1
					and detail.parent = entry.name
					and detail.item_code = %s''', (self.name, d.item_code))[0][0]

			d.db_set('transferred_qty', flt(transferred_qty), update_modified = False)


@frappe.whitelist()
def get_item_details(item, project = None):
	res = frappe.db.sql("""
		select stock_uom, description
		from `tabItem`
		where disabled=0
			and (end_of_life is null or end_of_life='0000-00-00' or end_of_life > %s)
			and name=%s
	""", (nowdate(), item), as_dict=1)

	if not res:
		return {}

	res = res[0]

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

	res['project'] = project or frappe.db.get_value('BOM', res['bom_no'], 'project')
	res.update(check_if_scrap_warehouse_mandatory(res["bom_no"]))

	return res

@frappe.whitelist()
def check_if_scrap_warehouse_mandatory(bom_no):
	res = {"set_scrap_wh_mandatory": False }
	if bom_no:
		bom = frappe.get_doc("BOM", bom_no)

		if len(bom.scrap_items) > 0:
			res["set_scrap_wh_mandatory"] = True

	return res

@frappe.whitelist()
def set_production_order_ops(name):
	po = frappe.get_doc('Production Order', name)
	po.set_production_order_operations()
	po.save()

@frappe.whitelist()
def make_stock_entry(production_order_id, purpose, qty=None):
	production_order = frappe.get_doc("Production Order", production_order_id)
	if not frappe.db.get_value("Warehouse", production_order.wip_warehouse, "is_group") \
			and not production_order.skip_transfer:
		wip_warehouse = production_order.wip_warehouse
	else:
		wip_warehouse = None

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = purpose
	stock_entry.production_order = production_order_id
	stock_entry.company = production_order.company
	stock_entry.from_bom = 1
	stock_entry.bom_no = production_order.bom_no
	stock_entry.use_multi_level_bom = production_order.use_multi_level_bom
	stock_entry.fg_completed_qty = qty or (flt(production_order.qty) - flt(production_order.produced_qty))

	if purpose=="Material Transfer for Manufacture":
		stock_entry.to_warehouse = wip_warehouse
		stock_entry.project = production_order.project
	else:
		stock_entry.from_warehouse = wip_warehouse
		stock_entry.to_warehouse = production_order.fg_warehouse
		additional_costs = get_additional_costs(production_order, fg_qty=stock_entry.fg_completed_qty)
		stock_entry.project = production_order.project
		stock_entry.set("additional_costs", additional_costs)

	stock_entry.get_items()
	return stock_entry.as_dict()

@frappe.whitelist()
def make_timesheet(production_order, company):
	timesheet = frappe.new_doc("Timesheet")
	timesheet.employee = ""
	timesheet.production_order = production_order
	timesheet.company = company
	return timesheet

@frappe.whitelist()
def add_timesheet_detail(timesheet, args):
	if isinstance(timesheet, text_type):
		timesheet = frappe.get_doc('Timesheet', timesheet)

	if isinstance(args, text_type):
		args = json.loads(args)

	timesheet.append('time_logs', args)
	return timesheet

@frappe.whitelist()
def get_default_warehouse():
	wip_warehouse = frappe.db.get_single_value("Manufacturing Settings",
		"default_wip_warehouse")
	fg_warehouse = frappe.db.get_single_value("Manufacturing Settings",
		"default_fg_warehouse")
	return {"wip_warehouse": wip_warehouse, "fg_warehouse": fg_warehouse}

@frappe.whitelist()
def make_new_timesheet(source_name, target_doc=None):
	po = frappe.get_doc('Production Order', source_name)
	ts = po.make_time_logs(open_new=True)

	if not ts or not ts.get('time_logs'):
		frappe.throw(_("Already completed"))

	return ts

@frappe.whitelist()
def stop_unstop(production_order, status):
	""" Called from client side on Stop/Unstop event"""

	if not frappe.has_permission("Production Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	pro_order = frappe.get_doc("Production Order", production_order)
	pro_order.update_status(status)
	pro_order.update_planned_qty()
	frappe.msgprint(_("Production Order has been {0}").format(status))
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
