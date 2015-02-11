# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json

from frappe.utils import flt, nowdate, cstr, get_datetime, getdate
from frappe import _
from frappe.model.document import Document
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no
from dateutil.relativedelta import relativedelta

class OverProductionError(frappe.ValidationError): pass
class StockOverProductionError(frappe.ValidationError): pass

form_grid_templates = {
	"operations": "templates/form_grid/production_order_grid.html"
}

class ProductionOrder(Document):
	def __setup__(self):
		self.holidays = frappe._dict()

	def validate(self):
		if self.docstatus == 0:
			self.status = "Draft"

		from erpnext.utilities import validate_status
		validate_status(self.status, ["Draft", "Submitted", "Stopped",
			"In Process", "Completed", "Cancelled"])

		if self.bom_no:
			validate_bom_no(self.production_item, self.bom_no)

		self.validate_sales_order()
		self.validate_warehouse()
		self.calculate_operating_cost()
		self.validate_delivery_date()

		from erpnext.utilities.transaction_base import validate_uom_is_integer
		validate_uom_is_integer(self, "stock_uom", ["qty", "produced_qty"])

	def validate_sales_order(self):
		if self.sales_order:
			so = frappe.db.sql("""select name, delivery_date from `tabSales Order`
				where name=%s and docstatus = 1""", self.sales_order, as_dict=1)

			if len(so):
				if not self.expected_delivery_date:
					self.expected_delivery_date = so[0].delivery_date

				self.validate_production_order_against_so()
			else:
				frappe.throw(_("Sales Order {0} is not valid").format(self.sales_order))

	def validate_warehouse(self):
		from erpnext.stock.utils import validate_warehouse_company

		for w in [self.fg_warehouse, self.wip_warehouse]:
			validate_warehouse_company(w, self.company)

	def calculate_operating_cost(self):
		self.planned_operating_cost, self.actual_operating_cost = 0.0, 0.0
		for d in self.get("operations"):
			d.actual_operating_cost = flt(d.hour_rate) * flt(d.actual_operation_time) / 60

			self.planned_operating_cost += flt(d.planned_operating_cost)
			self.actual_operating_cost += flt(d.actual_operating_cost)

		variable_cost = self.actual_operating_cost if self.actual_operating_cost else self.planned_operating_cost
		self.total_operating_cost = flt(self.additional_operating_cost) + flt(variable_cost)

	def validate_production_order_against_so(self):
		# already ordered qty
		ordered_qty_against_so = frappe.db.sql("""select sum(qty) from `tabProduction Order`
			where production_item = %s and sales_order = %s and docstatus < 2 and name != %s""",
			(self.production_item, self.sales_order, self.name))[0][0]

		total_qty = flt(ordered_qty_against_so) + flt(self.qty)

		# get qty from Sales Order Item table
		so_item_qty = frappe.db.sql("""select sum(qty) from `tabSales Order Item`
			where parent = %s and item_code = %s""",
			(self.sales_order, self.production_item))[0][0]
		# get qty from Packing Item table
		dnpi_qty = frappe.db.sql("""select sum(qty) from `tabPacked Item`
			where parent = %s and parenttype = 'Sales Order' and item_code = %s""",
			(self.sales_order, self.production_item))[0][0]
		# total qty in SO
		so_qty = flt(so_item_qty) + flt(dnpi_qty)

		if total_qty > so_qty:
			frappe.throw(_("Cannot produce more Item {0} than Sales Order quantity {1}").format(self.production_item,
				so_qty), OverProductionError)

	def stop_unstop(self, status):
		""" Called from client side on Stop/Unstop event"""
		self.update_status(status)
		qty = (flt(self.qty)-flt(self.produced_qty)) * ((status == 'Stopped') and -1 or 1)
		self.update_planned_qty(qty)
		frappe.msgprint(_("Production Order status is {0}").format(status))


	def update_status(self, status=None):
		if not status:
			status = self.status

		if status != 'Stopped':
			stock_entries = frappe._dict(frappe.db.sql("""select purpose, sum(fg_completed_qty)
				from `tabStock Entry` where production_order=%s and docstatus=1
				group by purpose""", self.name))

			status = "Submitted"
			if stock_entries:
				status = "In Process"
				produced_qty = stock_entries.get("Manufacture")
				if flt(produced_qty) == flt(self.qty):
					status = "Completed"

		if status != self.status:
			self.db_set("status", status)

	def update_produced_qty(self):
		produced_qty = frappe.db.sql("""select sum(fg_completed_qty)
			from `tabStock Entry` where production_order=%s and docstatus=1
			and purpose='Manufacture'""", self.name)
		produced_qty = flt(produced_qty[0][0]) if produced_qty else 0

		if produced_qty > self.qty:
			frappe.throw(_("Manufactured quantity {0} cannot be greater than planned quanitity {1} in Production Order {2}").format(produced_qty, self.qty, self.name), StockOverProductionError)

		self.db_set("produced_qty", produced_qty)

	def on_submit(self):
		if not self.wip_warehouse:
			frappe.throw(_("Work-in-Progress Warehouse is required before Submit"))
		if not self.fg_warehouse:
			frappe.throw(_("For Warehouse is required before Submit"))
		frappe.db.set(self,'status', 'Submitted')
		self.update_planned_qty(self.qty)


	def on_cancel(self):
		# Check whether any stock entry exists against this Production Order
		stock_entry = frappe.db.sql("""select name from `tabStock Entry`
			where production_order = %s and docstatus = 1""", self.name)
		if stock_entry:
			frappe.throw(_("Cannot cancel because submitted Stock Entry {0} exists").format(stock_entry[0][0]))

		frappe.db.set(self,'status', 'Cancelled')
		self.update_planned_qty(-self.qty)

	def update_planned_qty(self, qty):
		"""update planned qty in bin"""
		args = {
			"item_code": self.production_item,
			"warehouse": self.fg_warehouse,
			"posting_date": nowdate(),
			"planned_qty": flt(qty)
		}
		from erpnext.stock.utils import update_bin
		update_bin(args)

	def set_production_order_operations(self):
		"""Fetch operations from BOM and set in 'Production Order'"""

		self.set('operations', [])

		operations = frappe.db.sql("""select operation, opn_description, workstation,
			hour_rate, time_in_mins, operating_cost as "planned_operating_cost", "Pending" as status
			from `tabBOM Operation` where parent = %s""", self.bom_no, as_dict=1)

		self.set('operations', operations)

		self.plan_operations()
		self.calculate_operating_cost()

	def plan_operations(self):
		if self.planned_start_date:
			scheduled_datetime = self.planned_start_date
			for d in self.get('operations'):
				while getdate(scheduled_datetime) in self.get_holidays(d.workstation):
					scheduled_datetime = get_datetime(scheduled_datetime) + relativedelta(days=1)

				d.planned_start_time = scheduled_datetime
				scheduled_datetime = get_datetime(scheduled_datetime) + relativedelta(minutes=d.time_in_mins)
				d.planned_end_time = scheduled_datetime

			self.planned_end_date = scheduled_datetime


	def get_holidays(self, workstation):
		holiday_list = frappe.db.get_value("Workstation", workstation, "holiday_list")

		if holiday_list not in self.holidays:
			holiday_list_days = [getdate(d[0]) for d in frappe.get_all("Holiday", fields=["holiday_date"],
				filters={"parent": holiday_list}, order_by="holiday_date", limit_page_length=0, as_list=1)]

			self.holidays[holiday_list] = holiday_list_days

		return self.holidays[holiday_list]

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
		if self.get("operations"):
			actual_date = frappe.db.sql("""select min(actual_start_time) as start_date, max(actual_end_time) as end_date from `tabProduction Order Operation`
				where parent = %s and docstatus=1""", self.name, as_dict=1)[0]
			self.actual_start_date = actual_date.start_date
			self.actual_end_date = actual_date.end_date
		else:
			self.actual_start_date = None
			self.actual_end_date = None
			
	def validate_delivery_date(self):
		if self.planned_start_date and self.expected_delivery_date and getdate(self.expected_delivery_date) < getdate(self.planned_start_date):
			frappe.throw(_("Expected Delivery Date cannot be greater than Planned Start Date"))
			
		if self.planned_end_date and self.expected_delivery_date and getdate(self.expected_delivery_date) < getdate(self.planned_end_date):
			frappe.msgprint(_("Production might not be able to finish by the Expected Delivery Date."))

@frappe.whitelist()
def get_item_details(item):
	res = frappe.db.sql("""select stock_uom, description
		from `tabItem` where (ifnull(end_of_life, "0000-00-00")="0000-00-00" or end_of_life > now())
		and name=%s""", item, as_dict=1)

	if not res:
		return {}

	res = res[0]
	res["bom_no"] = frappe.db.get_value("BOM", filters={"item": item, "is_default": 1})
	return res

@frappe.whitelist()
def make_stock_entry(production_order_id, purpose, qty=None):
	production_order = frappe.get_doc("Production Order", production_order_id)

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = purpose
	stock_entry.production_order = production_order_id
	stock_entry.company = production_order.company
	stock_entry.bom_no = production_order.bom_no
	stock_entry.additional_operating_cost = production_order.additional_operating_cost
	stock_entry.use_multi_level_bom = production_order.use_multi_level_bom
	stock_entry.fg_completed_qty = qty or (flt(production_order.qty) - flt(production_order.produced_qty))

	if purpose=="Material Transfer":
		stock_entry.to_warehouse = production_order.wip_warehouse
	else:
		stock_entry.from_warehouse = production_order.wip_warehouse
		stock_entry.to_warehouse = production_order.fg_warehouse

	stock_entry.get_items()
	return stock_entry.as_dict()

@frappe.whitelist()
def get_events(start, end, filters=None):
	from frappe.desk.reportview import build_match_conditions
	if not frappe.has_permission("Production Order"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	conditions = build_match_conditions("Production Order")
	conditions = conditions and (" and " + conditions) or ""
	if filters:
		filters = json.loads(filters)
		for key in filters:
			if filters[key]:
				conditions += " and " + key + ' = "' + filters[key].replace('"', '\"') + '"'

	data = frappe.db.sql("""select name,production_item, production_start_date, production_end_date
		from `tabProduction Order`
		where ((ifnull(production_start_date, '0000-00-00')!= '0000-00-00') \
				and (production_start_date between %(start)s and %(end)s) \
			or ((ifnull(production_start_date, '0000-00-00')!= '0000-00-00') \
				and production_end_date between %(start)s and %(end)s)) {conditions}
		""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})
	return data

@frappe.whitelist()
def make_time_log(name, operation, from_time, to_time, qty=None,  project=None, workstation=None):
	time_log =  frappe.new_doc("Time Log")
	time_log.time_log_for = 'Manufacturing'
	time_log.from_time = from_time
	time_log.to_time = to_time
	time_log.production_order = name
	time_log.project = project
	time_log.operation= operation
	time_log.workstation= workstation
	time_log.activity_type= "Manufacturing"
	time_log.completed_qty = flt(qty)
	if from_time and to_time :
		time_log.calculate_total_hours()
	return time_log

@frappe.whitelist()
def auto_make_time_log(production_order_id):
	if frappe.db.get_value("Time Log", filters={"production_order": production_order_id, "docstatus":1}):
		frappe.throw(_("Time logs already exists against this Production Order"))

	time_logs = []
	prod_order = frappe.get_doc("Production Order", production_order_id)

	for d in prod_order.operations:
		operation = cstr(d.idx) + ". " + d.operation
		time_log = make_time_log(prod_order.name, operation, d.planned_start_time, d.planned_end_time,
			flt(prod_order.qty) - flt(d.completed_qty), prod_order.project_name, d.workstation)
		time_log.save()
		time_logs.append(time_log.name)
	if time_logs:
		frappe.msgprint(_("Time Logs created:") + "\n" + "\n".join(time_logs))
