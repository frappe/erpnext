# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from email_reply_parser import EmailReplyParser
from frappe.utils import flt, cint, get_url, cstr, nowtime, get_time, today, get_datetime, add_days, ceil, getdate
from erpnext.controllers.queries import get_filters_cond
from frappe.desk.reportview import get_match_cond
from erpnext.hr.doctype.daily_work_summary.daily_work_summary import get_users_email
from erpnext.hr.doctype.holiday_list.holiday_list import is_holiday
from erpnext.stock.get_item_details import get_applies_to_details
from frappe.model.naming import set_name_by_naming_series
from frappe.model.utils import get_fetch_values
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact, get_all_contact_nos
from erpnext.controllers.status_updater import StatusUpdater
from erpnext.projects.doctype.project_status.project_status import get_auto_project_status, set_manual_project_status,\
	get_valid_manual_project_status_names, is_manual_project_status, validate_project_status_for_transaction
from six import string_types
from erpnext.vehicles.vehicle_checklist import get_default_vehicle_checklist_items, set_missing_checklist
from erpnext.vehicles.doctype.vehicle_log.vehicle_log import get_customer_vehicle_selector_data
from frappe.model.meta import get_field_precision
import json


force_applies_to_fields = ("vehicle_chassis_no", "vehicle_engine_no", "vehicle_license_plate", "vehicle_unregistered",
	"vehicle_color", "applies_to_item", "applies_to_item_name", "applies_to_variant_of", "applies_to_variant_of_name",
	"vehicle_owner_name", "vehicle_warranty_no", "vehicle_delivery_date")

force_customer_fields = ("customer_name",
	"tax_id", "tax_cnic", "tax_strn", "tax_status",
	"address_display", "contact_display", "contact_email",
	"secondary_contact_display")

vehicle_change_fields = [
	('change_vehicle_license_plate', 'license_plate'),
	('change_vehicle_unregistered', 'unregistered'),
	('change_vehicle_warranty_no', 'warranty_no'),
	('change_vehicle_delivery_date', 'delivery_date')
]


class Project(StatusUpdater):
	def __init__(self, *args, **kwargs):
		super(Project, self).__init__(*args, **kwargs)
		self.sales_data = frappe._dict()
		self.invoices = []

	def get_feed(self):
		return '{0}: {1}'.format(_(self.status), frappe.safe_decode(self.project_name or self.name))

	def autoname(self):
		project_naming_by = frappe.defaults.get_global_default('project_naming_by')
		if project_naming_by == 'Project Name':
			self.name = self.project_name
		else:
			set_name_by_naming_series(self, 'project_number')

	def onload(self):
		self.set_onload('activity_summary', self.get_activity_summary())
		self.set_onload('default_vehicle_checklist_items', get_default_vehicle_checklist_items('vehicle_checklist'))
		self.set_onload('default_customer_request_checklist_items', get_default_vehicle_checklist_items('customer_request_checklist'))
		self.set_onload('cant_change_fields', self.get_cant_change_fields())
		self.set_onload('valid_manual_project_status_names', get_valid_manual_project_status_names(self))
		self.set_onload('is_manual_project_status', is_manual_project_status(self.project_status))
		self.set_onload('contact_nos', get_all_contact_nos('Customer', self.customer))

		if self.meta.has_field('applies_to_vehicle'):
			self.set_onload('customer_vehicle_selector_data', get_customer_vehicle_selector_data(self.customer,
				self.get('applies_to_vehicle')))

		self.reset_quick_change_fields()
		self.set_missing_checklist()

		self.sales_data = self.get_project_sales_data(get_sales_invoice=True)
		self.set_sales_data_html_onload(self.sales_data)

	def before_print(self):
		self.company_address_doc = erpnext.get_company_address(self)
		self.sales_data = self.get_project_sales_data(get_sales_invoice=True)
		self.get_sales_invoice_names()

	def validate(self):
		self.quick_change_master_details()

		if self.status not in ['Completed', 'Closed']:
			self.set_missing_values()

		self.validate_vehicle_booking_order()
		self.validate_appointment()
		self.validate_phone_nos()
		self.validate_project_type()
		self.validate_applies_to()
		self.validate_readings()
		self.validate_depreciation()

		self.set_percent_complete()
		self.set_vehicle_status()
		self.set_project_date()
		self.set_billing_and_delivery_status()
		self.set_costing()

		self.set_status()

		self.set_title()

		self.validate_cant_change()

		self.send_welcome_email()

		self._previous_appointment = self.db_get('appointment')

	def on_update(self):
		self.update_appointment()
		if 'Vehicles' in frappe.get_active_domains():
			self.update_odometer()

	def after_insert(self):
		self.set_project_in_sales_order_and_quotation()

	def after_delete(self):
		self.update_appointment()
		self.update_vehicle_booking_order_pdi_status()

	def set_title(self):
		if self.project_name:
			self.title = self.project_name
		elif self.customer_name or self.customer:
			self.title = self.customer_name or self.customer
		else:
			self.title = self.name

	def set_billing_and_delivery_status(self, update=False, update_modified=False):
		sales_data = self.get_project_sales_data(get_sales_invoice=False)
		self.total_billable_amount = sales_data.totals.grand_total
		self.customer_billable_amount = sales_data.totals.customer_grand_total
		self.total_billed_amount = self.get_billed_amount()

		sales_orders = frappe.get_all("Sales Order", fields=['per_completed', 'per_delivered', 'status', 'skip_delivery_note'], filters={
			"project": self.name, "docstatus": 1
		})
		delivery_notes = frappe.get_all("Delivery Note", fields=['per_completed', 'status'], filters={
			"project": self.name, "docstatus": 1, "is_return": 0,
		})
		sales_invoices = self.get_sales_invoices()

		self.billing_status, self.to_bill = self.get_billing_status(sales_orders, delivery_notes, sales_invoices, self.total_billed_amount)
		self.delivery_status, self.to_deliver = self.get_delivery_status(sales_orders, delivery_notes)

		if update:
			self.db_set({
				'total_billable_amount': self.total_billable_amount,
				'customer_billable_amount': self.customer_billable_amount,
				'total_billed_amount': self.total_billed_amount,
				'billing_status': self.billing_status,
				'to_bill': self.to_bill,
				'delivery_status': self.delivery_status,
				'to_deliver': self.to_deliver,
			}, None, update_modified=update_modified)

	def get_billing_status(self, sales_orders, delivery_notes, sales_invoices, total_billed_amount):
		has_billables = False
		has_unbilled = False
		has_sales_invoice = False

		for d in sales_orders + delivery_notes:
			if d.status != "Closed":
				has_billables = True
				if d.per_completed < 99.99:
					has_unbilled = True

		if sales_invoices:
			has_sales_invoice = True

		if has_billables:
			if has_sales_invoice:
				if has_unbilled:
					if flt(total_billed_amount) > 0:
						billing_status = "Partly Billed"
						to_bill = 1
					else:
						billing_status = "Not Billed"
						to_bill = 1
				else:
					billing_status = "Fully Billed"
					to_bill = 0
			else:
				billing_status = "Not Billed"
				to_bill = 1
		else:
			if has_sales_invoice:
				billing_status = "Fully Billed"
				to_bill = 0
			else:
				billing_status = "Not Applicable"
				to_bill = 0

		return billing_status, to_bill

	def get_delivery_status(self, sales_orders, delivery_notes):
		has_deliverables = False
		has_undelivered = False
		has_delivery_note = False

		if delivery_notes:
			has_delivery_note = True

		for d in sales_orders:
			if d.status != 'Closed' and not d.skip_delivery_note:
				has_deliverables = True
				if d.per_delivered < 99.99:
					has_undelivered = True

		if has_deliverables:
			if has_delivery_note:
				if has_undelivered:
					delivery_status = "Partly Delivered"
					to_deliver = 1
				else:
					delivery_status = "Fully Delivered"
					to_deliver = 0
			else:
				delivery_status = "Not Delivered"
				to_deliver = 1
		else:
			if has_delivery_note:
				delivery_status = "Fully Delivered"
				to_deliver = 0
			else:
				delivery_status = "Not Applicable"
				to_deliver = 0

		return delivery_status, to_deliver

	def get_billed_amount(self):
		directly_billed = frappe.db.sql("""
			select sum(base_grand_total)
			from `tabSales Invoice`
			where project = %s and docstatus = 1
		""", self.name)
		directly_billed = flt(directly_billed[0][0]) if directly_billed else 0

		indirectly_billed = frappe.db.sql("""
			select sum(i.base_tax_inclusive_amount)
			from `tabSales Invoice Item` i
			inner join `tabSales Invoice` p on p.name = i.parent
			where i.project = %(project)s and ifnull(p.project, '') != %(project)s and p.docstatus = 1
		""", {'project': self.name})
		indirectly_billed = flt(indirectly_billed[0][0]) if indirectly_billed else 0

		grand_total_precision = get_field_precision(frappe.get_meta("Sales Invoice").get_field("grand_total"),
			currency=frappe.get_cached_value('Company', self.company, "default_currency"))
		return flt(directly_billed + indirectly_billed, grand_total_precision)

	def set_costing(self, update=False, update_modified=False):
		self.set_sales_amount(update=update, update_modified=update_modified)
		self.set_timesheet_values(update=update, update_modified=update_modified)
		self.set_expense_claim_values(update=update, update_modified=update_modified)
		self.set_purchase_values(update=update, update_modified=update_modified)
		self.set_material_consumed_cost(update=update, update_modified=update_modified)
		self.set_gross_margin(update=update, update_modified=update_modified)

	def set_sales_amount(self, update=False, update_modified=False):
		sales_data = self.get_project_sales_data(get_sales_invoice=True)
		self.total_sales_amount = sales_data.totals.net_total
		self.stock_sales_amount = sales_data.stock_items.net_total
		self.service_sales_amount = sales_data.service_items.net_total

		if update:
			self.db_set({
				'total_sales_amount': self.total_sales_amount,
				'stock_sales_amount': self.stock_sales_amount,
				'service_sales_amount': self.service_sales_amount,
			}, None, update_modified=update_modified)

	def set_timesheet_values(self, update=False, update_modified=False):
		time_sheet_data = frappe.db.sql("""
			select
				sum(costing_amount) as costing_amount,
				sum(billing_amount) as billing_amount,
				min(from_time) as start_date,
				max(to_time) as end_date,
				sum(hours) as time
			from `tabTimesheet Detail`
			where project = %s and docstatus = 1
		""", self.name, as_dict=1)[0]

		self.actual_start_date = time_sheet_data.start_date
		self.actual_end_date = time_sheet_data.end_date

		self.timesheet_costing_amount = flt(time_sheet_data.costing_amount)
		self.timesheet_billable_amount = flt(time_sheet_data.billing_amount)
		self.actual_time = flt(time_sheet_data.time)

		if update:
			self.db_set({
				'actual_start_date': self.actual_start_date,
				'actual_end_date': self.actual_end_date,
				'timesheet_costing_amount': self.timesheet_costing_amount,
				'timesheet_billable_amount': self.timesheet_billable_amount,
				'actual_time': self.actual_time,
			}, None, update_modified=update_modified)

	def set_expense_claim_values(self, update=False, update_modified=False):
		expense_claim_data = frappe.db.sql("""
			select sum(sanctioned_amount) as total_sanctioned_amount
			from `tabExpense Claim Detail`
			where project = %s and docstatus = 1
		""", self.name, as_dict=1)[0]

		self.total_expense_claim = flt(expense_claim_data.total_sanctioned_amount)

		if update:
			self.db_set({
				'total_expense_claim': self.total_expense_claim,
			}, None, update_modified=update_modified)

	def set_purchase_values(self, update=False, update_modified=False):
		total_purchase_cost = frappe.db.sql("""
			select sum(base_net_amount)
			from `tabPurchase Invoice Item`
			where project = %s and docstatus=1
		""", self.name)

		self.total_purchase_cost = flt(total_purchase_cost[0][0]) if total_purchase_cost else 0

		if update:
			self.db_set({
				'total_purchase_cost': self.total_purchase_cost,
			}, None, update_modified=update_modified)

	def set_material_consumed_cost(self, update=False, update_modified=False):
		amount = frappe.db.sql("""
			select ifnull(sum(sed.amount), 0)
			from `tabStock Entry` se, `tabStock Entry Detail` sed
			where se.docstatus = 1 and se.project = %s and sed.parent = se.name
				and (sed.t_warehouse is null or sed.t_warehouse = '')
		""", self.name, as_list=1)
		amount = flt(amount[0][0]) if amount else 0

		additional_costs = frappe.db.sql("""
			select ifnull(sum(sed.amount), 0)
			from `tabStock Entry` se, `tabStock Entry Taxes and Charges` sed
			where se.docstatus = 1 and se.project = %s and sed.parent = se.name
				and se.purpose = 'Manufacture'""", self.name, as_list=1)
		additional_cost_amt = flt(additional_costs[0][0]) if additional_costs else 0

		amount += additional_cost_amt

		self.total_consumed_material_cost = amount

		if update:
			self.db_set({
				'total_consumed_material_cost': self.total_consumed_material_cost,
			}, None, update_modified=update_modified)

	def set_gross_margin(self, update=False, update_modified=False):
		total_revenue = flt(self.total_sales_amount)
		total_expense = (flt(self.timesheet_costing_amount) + flt(self.total_expense_claim)
			+ flt(self.total_purchase_cost) + flt(self.total_consumed_material_cost))

		self.gross_margin = total_revenue - total_expense
		self.per_gross_margin = self.gross_margin / total_revenue * 100 if total_revenue else 0

		if update:
			self.db_set({
				'gross_margin': self.gross_margin,
				'per_gross_margin': self.per_gross_margin,
			}, None, update_modified=update_modified)

	def set_percent_complete(self, update=False, update_modified=False):
		if self.percent_complete_method == "Manual":
			if self.status == "Completed":
				self.percent_complete = 100
			return

		total = frappe.db.count('Task', dict(project=self.name))

		if not total:
			self.percent_complete = 0
		else:
			if (self.percent_complete_method == "Task Completion" and total > 0) or (not self.percent_complete_method and total > 0):
				completed = frappe.db.sql("""
					select count(name)
					from tabTask where
					project=%s and status in ('Cancelled', 'Completed')
				""", self.name)[0][0]
				self.percent_complete = flt(flt(completed) / total * 100, 2)

			if self.percent_complete_method == "Task Progress" and total > 0:
				progress = frappe.db.sql("""select sum(progress) from tabTask where project=%s""", self.name)[0][0]
				self.percent_complete = flt(flt(progress) / total, 2)

			if self.percent_complete_method == "Task Weight" and total > 0:
				weight_sum = frappe.db.sql("""select sum(task_weight) from tabTask where project=%s""", self.name)[0][0]
				weighted_progress = frappe.db.sql("""select progress, task_weight from tabTask where project=%s""", self.name, as_dict=1)
				pct_complete = 0
				for row in weighted_progress:
					pct_complete += row["progress"] * frappe.utils.safe_div(row["task_weight"], weight_sum)
				self.percent_complete = flt(flt(pct_complete), 2)

		if update:
			self.db_set({
				'percent_complete': self.percent_complete,
			}, None, update_modified=update_modified)

	def set_ready_to_close(self, update=True):
		previous_ready_to_close = self.ready_to_close

		self.ready_to_close = 1

		if not previous_ready_to_close:
			self.ready_to_close_dt = frappe.utils.now_datetime()

		self.status = "To Close"

		if update:
			self.db_set({
				'ready_to_close': self.ready_to_close,
				'ready_to_close_dt': self.ready_to_close_dt,
				'status': self.status,
			}, None)

	def reopen_status(self, update=True):
		self.ready_to_close = 0
		self.ready_to_close_dt = None
		self.status = "Open"

		if update:
			self.db_set({
				'ready_to_close': self.ready_to_close,
				'ready_to_close_dt': self.ready_to_close_dt,
				'status': self.status,
			}, None)

	def validate_project_status_for_transaction(self, doc):
		validate_project_status_for_transaction(self, doc)

	def set_status(self, update=False, status=None, update_modified=True, reset=False):
		previous_status = self.status
		previous_project_status = self.project_status
		previous_indicator_color = self.indicator_color

		# set/reset manual status
		if reset:
			self.project_status = None
		elif status:
			set_manual_project_status(self, status)

		# get evaulated status
		project_status = get_auto_project_status(self)

		# no applicable status
		if not project_status:
			return

		# set status
		self.project_status = project_status.name
		self.status = project_status.status
		self.indicator_color = project_status.indicator_color

		# status comment only if project status changed
		if self.project_status != previous_project_status and not self.is_new():
			self.add_comment("Label", _(self.project_status))

		# update database only if changed
		if update:
			if self.project_status != previous_project_status or self.status != previous_status\
					or cstr(self.indicator_color) != cstr(previous_indicator_color):
				self.db_set({
					'project_status': self.project_status,
					'status': self.status,
					'indicator_color': self.indicator_color,
				}, None, update_modified=update_modified)

	def validate_cant_change(self):
		if self.is_new():
			return

		fields = self.get_cant_change_fields()
		cant_change_fields = [f for f, cant_change in fields.items() if cant_change and self.meta.get_field(f) and self.meta.get_field(f).fieldtype != 'Table']

		if cant_change_fields:
			previous_values = frappe.db.get_value(self.doctype, self.name, cant_change_fields, as_dict=1)
			for f, old_value in previous_values.items():
				if cstr(self.get(f)) != cstr(old_value):
					label = self.meta.get_label(f)
					frappe.throw(_("Cannot change {0} because transactions already exist against this Project")
						.format(frappe.bold(label)))

	def get_cant_change_fields(self):
		vehicle_received = self.get('vehicle_received_date')
		has_sales_transaction = self.has_sales_transaction()
		has_vehicle_log = self.has_vehicle_log()
		return frappe._dict({
			'applies_to_vehicle': vehicle_received or has_vehicle_log,
			'project_workshop': vehicle_received,
			'customer': has_sales_transaction,
			'bill_to': has_sales_transaction and self.is_warranty_claim,
			'is_warranty_claim': has_sales_transaction and self.is_warranty_claim,
		})

	def has_sales_transaction(self):
		if getattr(self, '_has_sales_transaction', None):
			return self._has_sales_transaction

		if frappe.db.get_value("Sales Order", {'project': self.name, 'docstatus': 1})\
				or frappe.db.get_value("Sales Invoice", {'project': self.name, 'docstatus': 1})\
				or frappe.db.get_value("Delivery Note", {'project': self.name, 'docstatus': 1})\
				or frappe.db.get_value("Quotation", {'project': self.name, 'docstatus': 1}):
			self._has_sales_transaction = True
		else:
			self._has_sales_transaction = False

		return self._has_sales_transaction

	def has_vehicle_log(self):
		if getattr(self, '_has_vehicle_log', None):
			return self._has_vehicle_log

		if frappe.db.get_value("Vehicle Log", {'project': self.name, 'docstatus': 1}):
			self._has_vehicle_log = True
		else:
			self._has_vehicle_log = False

		return self._has_vehicle_log

	def validate_project_type(self):
		if self.status in ['Completed', 'Closed']:
			return

		if self.project_type:
			project_type = frappe.get_cached_doc("Project Type", self.project_type)

			if project_type.bill_to_mandatory and not self.get('bill_to'):
				frappe.throw(_("Bill To is mandatory for Project Type {0}").format(self.project_type))

			if project_type.insurance_company_mandatory and not self.get('insurance_company'):
				frappe.throw(_("Insurance Company is mandatory for Project Type {0}").format(self.project_type))

			if project_type.campaign_mandatory and not self.get('campaign'):
				frappe.throw(_("Campaign is mandatory for Project Type {0}").format(self.project_type))

			if project_type.previous_project_mandatory and not self.get('previous_project'):
				frappe.throw(_("{0} is mandatory for Project Type {1}")
					.format(self.meta.get_label('previous_project'), self.project_type))

	def validate_vehicle_booking_order(self):
		if self.get('vehicle_booking_order'):
			vehicle_booking_order = frappe.db.get_value("Vehicle Booking Order", self.vehicle_booking_order,
				['docstatus', 'status', 'customer', 'financer', 'transfer_customer', 'vehicle', 'item_code'], as_dict=1)

			if not vehicle_booking_order:
				frappe.throw(_("Vehicle Booking Order {0} does not exist").format(self.vehicle_booking_order))

			if vehicle_booking_order.status == "Cancelled Booking" or vehicle_booking_order.docstatus == 2:
				frappe.throw(_("Vehicle Booking Order {0} is cancelled").format(self.vehicle_booking_order))

			if vehicle_booking_order.docstatus != 1:
				frappe.throw(_("Vehicle Booking Order {0} is not submitted").format(self.vehicle_booking_order))

			if self.get('customer') and self.customer not in [vehicle_booking_order.customer, vehicle_booking_order.financer, vehicle_booking_order.transfer_customer]:
				frappe.throw(_("Customer does not match with Vehicle Booking Order {0}").format(self.vehicle_booking_order))

			if self.get('applies_to_vehicle') and self.applies_to_vehicle != vehicle_booking_order.vehicle:
				frappe.throw(_("Vehicle does not match with Vehicle Booking Order {0}").format(self.vehicle_booking_order))

			if self.get('applies_to_item') and self.applies_to_item != vehicle_booking_order.item_code:
				frappe.throw(_("Vehicle Variant Code does not match with Vehicle Booking Order {0}").format(self.vehicle_booking_order))

	def validate_appointment(self):
		if self.get('appointment'):
			appointment_details = frappe.db.get_value("Appointment", self.appointment,
				['name', 'status', 'docstatus'], as_dict=1)

			if not appointment_details:
				frappe.throw(_("Appointment {0} does not exist").format(self.appointment))

			if appointment_details.docstatus == 0:
				frappe.throw(_("{0} is not submitted").format(frappe.get_desk_link("Appointment", self.appointment)))
			if appointment_details.docstatus == 2:
				frappe.throw(_("{0} is cancelled").format(frappe.get_desk_link("Appointment", self.appointment)))
			if appointment_details.status == "Rescheduled":
				frappe.throw(_("{0} is {1}. Please select newer appointment instead")
					.format(frappe.get_desk_link("Appointment", self.appointment), frappe.bold(appointment_details.status)))

	def update_appointment(self):
		appointments = []
		if self.appointment:
			appointments.append(self.appointment)

		previous_appointment = self.get('_previous_appointment')
		if previous_appointment and previous_appointment not in appointments:
			appointments.append(previous_appointment)

		for appointment in appointments:
			doc = frappe.get_doc("Appointment", appointment)
			doc.set_status(update=True)
			doc.notify_update()

	def update_vehicle_booking_order_pdi_status(self):
		if self.get('vehicle_booking_order'):
			vbo = frappe.get_doc("Vehicle Booking Order", self.vehicle_booking_order)
			vbo.set_pdi_status(update=True)
			vbo.notify_update()

	def validate_phone_nos(self):
		if not self.get('contact_mobile') and self.get('contact_mobile_2'):
			self.contact_mobile = self.contact_mobile_2
			self.contact_mobile_2 = ''
		if self.get('contact_mobile') == self.get('contact_mobile_2'):
			self.contact_mobile_2 = ''

	def set_missing_values(self):
		self.set_appointment_details()
		self.set_customer_details()
		self.set_applies_to_details()
		self.set_missing_checklist()
		self.set_project_template_details()
		self.set_material_and_service_item_groups()

	def set_customer_details(self):
		args = self.as_dict()
		customer_details = get_customer_details(args)

		for k, v in customer_details.items():
			if self.meta.has_field(k) and not self.get(k) or k in force_customer_fields:
				self.set(k, v)

	def set_applies_to_details(self):
		args = self.as_dict()
		applies_to_details = get_applies_to_details(args, for_validate=True)

		for k, v in applies_to_details.items():
			if self.meta.has_field(k) and not self.get(k) or k in force_applies_to_fields:
				self.set(k, v)

	def set_missing_checklist(self):
		if self.meta.has_field('vehicle_checklist'):
			set_missing_checklist(self, 'vehicle_checklist')
		if self.meta.has_field('customer_request_checklist'):
			set_missing_checklist(self, 'customer_request_checklist')

	def get_checklist_rows(self, parentfield, rows=1):
		checklist = self.get(parentfield) or []
		per_row = ceil(len(checklist) / rows)

		out = []
		for i in range(rows):
			out.append([])

		for i, d in enumerate(checklist):
			row_id = i // per_row
			out[row_id].append(d)

		return out

	def set_project_template_details(self):
		for d in self.project_templates:
			if d.project_template and not d.project_template_name:
				d.project_template_name = frappe.get_cached_value("Project Template", d.project_template, "project_template_name")

	def set_appointment_details(self):
		if self.appointment:
			appointment_doc = frappe.get_doc("Appointment", self.appointment)

			self.appointment_dt = appointment_doc.scheduled_dt

			if not self.customer:
				customer = appointment_doc.get_customer()
				if customer:
					self.customer = customer

			if self.meta.has_field('applies_to_vehicle') and not self.get('applies_to_vehicle'):
				if appointment_doc.get('applies_to_vehicle'):
					self.applies_to_vehicle = appointment_doc.get('applies_to_vehicle')
		else:
			self.appointment_dt = None

	def set_material_and_service_item_groups(self):
		settings = frappe.get_cached_doc("Projects Settings", None)
		self.materials_item_group = settings.materials_item_group
		self.consumables_item_group = settings.consumables_item_group
		self.lubricants_item_group = settings.lubricants_item_group
		self.sublet_item_group = settings.sublet_item_group

	def validate_readings(self):
		if self.meta.has_field('fuel_level'):
			if flt(self.fuel_level) < 0 or flt(self.fuel_level) > 100:
				frappe.throw(_("Fuel Level must be between 0% and 100%"))
		if self.meta.has_field('keys'):
			if cint(self.keys) < 0:
				frappe.throw(_("No of Keys cannot be negative"))

	def validate_applies_to(self):
		from erpnext.vehicles.utils import format_vehicle_fields
		if not self.get('applies_to_item'):
			format_vehicle_fields(self)

		if self.get('applies_to_item') and not self.get('project_workshop'):
			frappe.throw(_("Project Workshop is mandatory when Applies to Item is set"))

	def set_project_in_sales_order_and_quotation(self):
		if self.sales_order:
			frappe.db.set_value("Sales Order", self.sales_order, "project", self.name, notify=1)

			quotations = frappe.db.sql_list("""
				select distinct qtn.name
				from `tabQuotation` qtn
				inner join `tabSales Order Item` item on item.quotation = qtn.name
				where item.parent = %s and qtn.docstatus < 2 and ifnull(qtn.project, '') = ''
			""", self.sales_order)

			for quotation in quotations:
				frappe.db.set_value("Quotation", quotation, "project", self.name, notify=1)

	def quick_change_master_details(self):
		if not self._action:
			return

		if self.get('applies_to_vehicle'):
			vehicle_change_map = frappe._dict()
			for project_field, vehicle_field in vehicle_change_fields:
				if self.meta.has_field(project_field) and self.get(project_field):
					vehicle_change_map[vehicle_field] = self.get(project_field)

			if vehicle_change_map:
				if vehicle_change_map.get('unregistered'):
					vehicle_change_map['license_plate'] = None
				if vehicle_change_map.get('license_plate'):
					vehicle_change_map['unregistered'] = 0

				frappe.set_value("Vehicle", self.applies_to_vehicle, vehicle_change_map)

		self.reset_quick_change_fields()

	def reset_quick_change_fields(self):
		for project_field, vehicle_field in vehicle_change_fields:
			df = self.meta.get_field(project_field)
			if df:
				if df.fieldtype in frappe.model.numeric_fieldtypes:
					self.set(project_field, 0)
				else:
					self.set(project_field, None)

	def update_odometer(self):
		from erpnext.vehicles.doctype.vehicle_log.vehicle_log import make_vehicle_log, get_project_odometer

		if not self.meta.has_field('applies_to_vehicle'):
			return

		if self.get('applies_to_vehicle'):
			reload = False

			odo = get_project_odometer(self.name, self.applies_to_vehicle)
			if not odo.vehicle_first_odometer and self.vehicle_first_odometer:
				make_vehicle_log(self.applies_to_vehicle, odometer=self.vehicle_first_odometer, project=self.name,
					from_project_update=True)
				reload = True

			if reload:
				odo = get_project_odometer(self.name, self.applies_to_vehicle)
			if self.vehicle_last_odometer and self.vehicle_last_odometer > odo.vehicle_last_odometer:
				make_vehicle_log(self.applies_to_vehicle, odometer=self.vehicle_last_odometer, project=self.name,
					from_project_update=True)
				reload = True

			if reload:
				self.vehicle_first_odometer, self.vehicle_last_odometer = self.db_get(['vehicle_first_odometer',
					'vehicle_last_odometer'])
			else:
				odo = get_project_odometer(self.name, self.applies_to_vehicle)
				self.db_set({
					"vehicle_first_odometer": odo.vehicle_first_odometer,
					"vehicle_last_odometer": odo.vehicle_last_odometer,
				})

	def validate_depreciation(self):
		if not self.insurance_company:
			self.default_depreciation_percentage = 0
			self.non_standard_depreciation = []
			return

		if flt(self.default_depreciation_percentage) > 100:
			frappe.throw(_("Default Depreciation Rate cannot be greater than 100%"))
		elif flt(self.default_depreciation_percentage) < 0:
			frappe.throw(_("Default Depreciation Rate cannot be negative"))

		item_codes_visited = set()
		for d in self.non_standard_depreciation:
			if flt(d.depreciation_percentage) > 100:
				frappe.throw(_("Row #{0}: Depreciation Rate cannot be greater than 100%").format(d.idx))
			elif flt(d.depreciation_percentage) < 0:
				frappe.throw(_("Row #{0}: Depreciation Rate cannot be negative").format(d.idx))

			if d.depreciation_item_code in item_codes_visited:
				frappe.throw(_("Row #{0}: Duplicate Non Standard Depreciation row for Item {1}")
					.format(d.idx, frappe.bold(d.depreciation_item_code)))

			item_codes_visited.add(d.depreciation_item_code)

	def copy_from_template(self):
		'''
		Copy tasks from template
		'''
		if self.project_template and not frappe.db.get_all('Task', dict(project = self.name), limit=1):

			# has a template, and no loaded tasks, so lets create
			if not self.expected_start_date:
				# project starts today
				self.expected_start_date = today()

			template = frappe.get_doc('Project Template', self.project_template)

			if not self.project_type:
				self.project_type = template.project_type

			# create tasks from template
			for task in template.tasks:
				frappe.get_doc(dict(
					doctype = 'Task',
					subject = task.subject,
					project = self.name,
					status = 'Open',
					exp_start_date = add_days(self.expected_start_date, task.start),
					exp_end_date = add_days(self.expected_start_date, task.start + task.duration),
					description = task.description,
					task_weight = task.task_weight
				)).insert()

	def set_sales_data_html_onload(self, sales_data):
		currency = erpnext.get_company_currency(self.company)

		stock_items_html = frappe.render_template("erpnext/projects/doctype/project/project_items_table.html",
			{"doc": self, "data": sales_data.stock_items, "currency": currency,
				"title": _("Materials"), "show_delivery_note": True, "show_uom": True})
		service_items_html = frappe.render_template("erpnext/projects/doctype/project/project_items_table.html",
			{"doc": self, "data": sales_data.service_items, "currency": currency,
				"title": _("Services"), "show_delivery_note": False, "show_uom": False})

		sales_summary_html = frappe.render_template("erpnext/projects/doctype/project/project_sales_summary.html",
			{"doc": self, "currency": currency})

		self.set_onload('stock_items_html', stock_items_html)
		self.set_onload('service_items_html', service_items_html)
		self.set_onload('sales_summary_html', sales_summary_html)

	def get_project_sales_data(self, get_sales_invoice=True):
		sales_data = frappe._dict()
		sales_data.stock_items, sales_data.part_items, sales_data.lubricant_items = get_stock_items(self,
			get_sales_invoice=get_sales_invoice)
		sales_data.service_items, sales_data.labour_items, sales_data.sublet_items = get_service_items(self,
			get_sales_invoice=get_sales_invoice)
		sales_data.totals = get_totals_data([sales_data.stock_items, sales_data.service_items], self.company)

		return sales_data

	def get_sales_invoices(self):
		return frappe.db.sql("""
			select inv.name, inv.customer, inv.bill_to
			from `tabSales Invoice` inv
			where inv.docstatus = 1 and (inv.project = %(project)s or exists(
				select item.name from `tabSales Invoice Item` item
				where item.parent = inv.name and item.project = %(project)s))
			order by posting_date, posting_time, creation
		""", {'project': self.name}, as_dict=1)

	def get_invoice_for_vehicle_gate_pass(self):
		all_invoices = self.get_sales_invoices()
		direct_invoices = [d for d in all_invoices if d.customer == d.bill_to == self.customer]

		sales_invoice = None
		if len(all_invoices) == 1:
			sales_invoice = all_invoices[0].name
		elif len(direct_invoices) == 1:
			sales_invoice = direct_invoices[0].name

		return sales_invoice

	def get_sales_invoice_names(self):
		# Invoices
		invoices = self.get_sales_invoices()
		self.invoices = [d.name for d in invoices]

	def get_activity_summary(self):
		return frappe.db.sql("""
			select activity_type, sum(hours) as total_hours
			from `tabTimesheet Detail`
			where project=%s and docstatus < 2
			group by activity_type
			order by total_hours desc
		""", self.name, as_dict=True)

	def set_vehicle_status(self, update=False, update_modified=True):
		if not self.meta.has_field('vehicle_status'):
			return

		vehicle_service_receipts = None
		vehicle_gate_passes = None

		if self.get('applies_to_vehicle'):
			vehicle_service_receipts = frappe.db.get_all("Vehicle Service Receipt",
				{"project": self.name, "vehicle": self.applies_to_vehicle, "docstatus": 1},
				['name', 'posting_date', 'posting_time'],
				order_by="posting_date, posting_time, creation")
			vehicle_gate_passes = frappe.db.get_all("Vehicle Gate Pass",
				{"project": self.name, "vehicle": self.applies_to_vehicle, "docstatus": 1},
				['name', 'posting_date', 'posting_time'],
				order_by="posting_date, posting_time, creation")

		vehicle_service_receipt = frappe._dict()
		vehicle_gate_pass = frappe._dict()

		if vehicle_service_receipts:
			vehicle_service_receipt = vehicle_service_receipts[0]

		if vehicle_gate_passes:
			vehicle_gate_pass = vehicle_gate_passes[-1]

		self.vehicle_received_date = vehicle_service_receipt.posting_date
		self.vehicle_received_time = vehicle_service_receipt.posting_time

		self.vehicle_delivered_date = vehicle_gate_pass.posting_date
		self.vehicle_delivered_time = vehicle_gate_pass.posting_time

		self.set_project_date()

		if not self.get('applies_to_vehicle'):
			self.vehicle_status = "Not Applicable"
		elif not vehicle_service_receipt:
			self.vehicle_status = "Not Received"
		elif not vehicle_gate_pass:
			self.vehicle_status = "In Workshop"
		else:
			self.vehicle_status = "Delivered"

		if update:
			self.db_set({
				"vehicle_received_date": self.vehicle_received_date,
				"vehicle_received_time": self.vehicle_received_time,
				"vehicle_delivered_date": self.vehicle_delivered_date,
				"vehicle_delivered_time": self.vehicle_delivered_time,
				"vehicle_status": self.vehicle_status,
				"project_date": self.project_date
			}, update_modified=update_modified)

	def set_project_date(self):
		self.project_date = getdate(
			self.get('vehicle_received_date')
			or self.actual_start_date
			or self.expected_start_date
			or self.creation
		)

	def after_rename(self, old_name, new_name, merge=False):
		if old_name == self.copied_from:
			frappe.db.set_value('Project', new_name, 'copied_from', new_name)

	def send_welcome_email(self):
		url = get_url("/project/?name={0}".format(self.name))
		messages = (
			_("You have been invited to collaborate on the project: {0}".format(self.name)),
			url,
			_("Join")
		)

		content = """
		<p>{0}.</p>
		<p><a href="{1}">{2}</a></p>
		"""

		for user in self.users:
			if user.welcome_email_sent == 0:
				frappe.sendmail(user.user, subject=_("Project Collaboration Invitation"),
								content=content.format(*messages))
				user.welcome_email_sent = 1

	def get_item_groups_subtree(self, item_group):
		if (self.get('_item_group_subtree') or {}).get(item_group):
			return self._item_group_subtree[item_group]

		item_group_tree = []
		if item_group:
			item_group_tree = frappe.get_all("Item Group", {"name": ["subtree of", item_group]})
			item_group_tree = [d.name for d in item_group_tree]

		if not self.get('_item_group_subtree'):
			self._item_group_subtree = {}

		self._item_group_subtree[item_group] = item_group_tree

		return self._item_group_subtree[item_group]


def get_stock_items(project, get_sales_invoice=True):
	is_material_condition = "i.is_stock_item = 1"
	materials_item_groups = project.get_item_groups_subtree(project.materials_item_group)
	if materials_item_groups:
		is_material_condition = "(i.is_stock_item = 1 or i.item_group in ({0}))"\
			.format(", ".join([frappe.db.escape(d) for d in materials_item_groups]))

	dn_data = frappe.db.sql("""
		select p.name as delivery_note, i.sales_order,
			p.posting_date, p.posting_time, i.idx,
			i.item_code, i.item_name, i.description, i.item_group, i.is_stock_item,
			i.qty, i.uom,
			i.base_net_amount as net_amount,
			i.base_net_rate as net_rate,
			i.item_tax_detail, i.claim_customer, p.conversion_rate
		from `tabDelivery Note Item` i
		inner join `tabDelivery Note` p on p.name = i.parent
		where p.docstatus = 1 and {0}
			and p.project = %s
	""".format(is_material_condition), project.name, as_dict=1)
	set_sales_data_customer_amounts(dn_data, project)

	so_data = frappe.db.sql("""
		select p.name as sales_order,
			p.transaction_date, i.idx,
			i.item_code, i.item_name, i.description, i.item_group, i.is_stock_item,
			if(i.is_stock_item = 1, i.qty - i.delivered_qty, i.qty) as qty,
			i.qty as ordered_qty,
			i.delivered_qty,
			i.uom,
			if(i.is_stock_item = 1, i.base_net_amount * (i.qty - i.delivered_qty) / i.qty, i.base_net_amount) as net_amount,
			i.base_net_rate as net_rate,
			i.item_tax_detail, i.claim_customer, p.conversion_rate
		from `tabSales Order Item` i
		inner join `tabSales Order` p on p.name = i.parent
		where p.docstatus = 1 and {0}
			and (i.delivered_qty < i.qty or i.is_stock_item = 0)
			and i.qty > 0
			and (p.status != 'Closed' or exists(select sum(si_item.amount)
				from `tabSales Invoice Item` si_item
				where si_item.docstatus = 1 and si_item.sales_order_item = i.name and ifnull(si_item.delivery_note, '') = ''
				having sum(si_item.amount) > 0)
			)
			and p.project = %s
	""".format(is_material_condition), project.name, as_dict=1)
	set_sales_data_customer_amounts(so_data, project)

	sinv_data = frappe.db.sql("""
		select p.name as sales_invoice, i.delivery_note, i.sales_order,
			p.posting_date, p.posting_time, i.idx,
			i.item_code, i.item_name, i.description, i.item_group, i.is_stock_item,
			i.qty, i.uom,
			i.base_net_amount as net_amount,
			i.base_net_rate as net_rate,
			i.item_tax_detail, p.conversion_rate
		from `tabSales Invoice Item` i
		inner join `tabSales Invoice` p on p.name = i.parent
		where p.docstatus = 1 and {0} and ifnull(i.sales_order, '') = '' and ifnull(i.delivery_note, '') = ''
			and (p.project = %s or i.project = %s)
	""".format(is_material_condition), [project.name, project.name], as_dict=1)
	set_sales_data_customer_amounts(sinv_data, project)

	stock_data = get_items_data_template()
	parts_data = get_items_data_template()
	lubricants_data = get_items_data_template()

	lubricants_item_groups = project.get_item_groups_subtree(project.lubricants_item_group)
	for d in dn_data + so_data + sinv_data:
		stock_data['items'].append(d)

		if d.item_group in lubricants_item_groups:
			lubricants_data['items'].append(d.copy())
		else:
			parts_data['items'].append(d.copy())

	stock_data['items'] = sorted(stock_data['items'], key=lambda d: (cstr(d.posting_date), cstr(d.posting_time), d.idx))
	parts_data['items'] = sorted(parts_data['items'], key=lambda d: (cstr(d.posting_date), cstr(d.posting_time), d.idx))
	lubricants_data['items'] = sorted(lubricants_data['items'], key=lambda d: (cstr(d.posting_date), cstr(d.posting_time), d.idx))

	get_item_taxes(project, stock_data, project.company)
	post_process_items_data(stock_data)

	get_item_taxes(project, parts_data, project.company)
	post_process_items_data(parts_data)

	get_item_taxes(project, lubricants_data, project.company)
	post_process_items_data(lubricants_data)

	return stock_data, parts_data, lubricants_data


def get_service_items(project, get_sales_invoice=True):
	is_service_condition = "(i.is_stock_item = 0 and i.is_fixed_asset = 0)"
	materials_item_groups = project.get_item_groups_subtree(project.materials_item_group)
	if materials_item_groups:
		is_service_condition = "(i.is_stock_item = 0 and i.is_fixed_asset = 0 and i.item_group not in ({0}))"\
			.format(", ".join([frappe.db.escape(d) for d in materials_item_groups]))

	so_data = frappe.db.sql("""
		select p.name as sales_order,
			p.transaction_date,
			i.item_code, i.item_name, i.description, i.item_group, i.is_stock_item,
			i.qty, i.uom,
			i.base_net_amount as net_amount,
			i.base_net_rate as net_rate,
			i.item_tax_detail, i.claim_customer, p.conversion_rate
		from `tabSales Order Item` i
		inner join `tabSales Order` p on p.name = i.parent
		where p.docstatus = 1 and {0}
			and p.project = %s
		order by p.transaction_date, p.creation, i.idx
	""".format(is_service_condition), project.name, as_dict=1)
	set_sales_data_customer_amounts(so_data, project)

	sinv_data = []
	if get_sales_invoice:
		sinv_data = frappe.db.sql("""
			select p.name as sales_invoice, i.delivery_note, i.sales_order,
				p.posting_date as transaction_date,
				i.item_code, i.item_name, i.description, i.item_group, i.is_stock_item,
				i.qty, i.uom,
				i.base_net_amount as net_amount,
				i.base_net_rate as net_rate,
				i.item_tax_detail, p.conversion_rate
			from `tabSales Invoice Item` i
			inner join `tabSales Invoice` p on p.name = i.parent
			where p.docstatus = 1 and {0} and ifnull(i.sales_order, '') = ''
				and (p.project = %s or i.project = %s)
			order by p.posting_date, p.creation, i.idx
		""".format(is_service_condition), [project.name, project.name], as_dict=1)
	set_sales_data_customer_amounts(sinv_data, project)

	service_data = get_items_data_template()
	labour_data = get_items_data_template()
	sublet_data = get_items_data_template()

	sublet_item_groups = project.get_item_groups_subtree(project.sublet_item_group)
	for d in so_data + sinv_data:
		service_data['items'].append(d)

		if d.item_group in sublet_item_groups:
			sublet_data['items'].append(d.copy())
		else:
			labour_data['items'].append(d.copy())

	get_item_taxes(project, service_data, project.company)
	post_process_items_data(service_data)

	get_item_taxes(project, labour_data, project.company)
	post_process_items_data(labour_data)

	get_item_taxes(project, sublet_data, project.company)
	post_process_items_data(sublet_data)

	return service_data, labour_data, sublet_data


def get_items_data_template():
	return frappe._dict({
		'total_qty': 0,

		'net_total': 0,
		'customer_net_total': 0,

		'sales_tax_total': 0,
		'customer_sales_tax_total': 0,

		'service_tax_total': 0,
		'customer_service_tax_total': 0,

		'other_taxes_and_charges': 0,
		'customer_other_taxes_and_charges': 0,

		'taxes': {},
		'customer_taxes': {},

		'items': [],
	})


def set_sales_data_customer_amounts(data, project):
	set_depreciation_in_invoice_items(data, project)

	for d in data:
		d.has_customer_depreciation = 0

		if d.get('claim_customer') and project.customer and d.get('claim_customer') != project.customer:
			d.is_claim_item = 1
			d.customer_net_amount = 0
			d.customer_net_rate = 0
		else:
			d.is_claim_item = 0

			if project.insurance_company and project.bill_to and project.bill_to != project.customer:
				d.has_customer_depreciation = 1
				d.customer_net_amount = d.net_amount * flt(d.depreciation_percentage) / 100
				d.customer_net_rate = d.net_rate * flt(d.depreciation_percentage) / 100
			else:
				d.customer_net_amount = d.net_amount
				d.customer_net_rate = d.net_rate


def get_item_taxes(project, data, company):
	sales_tax_account = frappe.get_cached_value('Company', company, "sales_tax_account")
	service_tax_account = frappe.get_cached_value('Company', company, "service_tax_account")

	for d in data['items']:
		conversion_rate = flt(d.get('conversion_rate')) or 1

		d.setdefault('taxes', {})
		d.setdefault('customer_taxes', {})

		d.setdefault('sales_tax_amount', 0)
		d.setdefault('customer_sales_tax_amount', 0)

		d.setdefault('service_tax_amount', 0)
		d.setdefault('customer_service_tax_amount', 0)

		d.setdefault('other_taxes_and_charges', 0)
		d.setdefault('customer_other_taxes_and_charges', 0)

		if project.get('has_stin'):
			item_tax_detail = json.loads(d.item_tax_detail or '{}')
			for tax_row_name, amount in item_tax_detail.items():
				tax_account = frappe.db.get_value("Sales Taxes and Charges", tax_row_name, 'account_head', cache=1)
				if tax_account:
					tax_amount = flt(amount)
					tax_amount *= conversion_rate

					customer_tax_amount = 0 if d.get('is_claim_item') else flt(amount)
					if d.has_customer_depreciation:
						customer_tax_amount *= d.depreciation_percentage / 100

					customer_tax_amount *= conversion_rate

					if flt(d.ordered_qty):
						tax_amount = tax_amount * flt(d.qty) / flt(d.ordered_qty)
						customer_tax_amount = customer_tax_amount * flt(d.qty) / flt(d.ordered_qty)

					d.taxes.setdefault(tax_account, 0)
					d.taxes[tax_account] += tax_amount

					d.customer_taxes.setdefault(tax_account, 0)
					d.customer_taxes[tax_account] += customer_tax_amount

					if tax_account == sales_tax_account:
						d.sales_tax_amount += tax_amount
						d.customer_sales_tax_amount += customer_tax_amount
					elif tax_account == service_tax_account:
						d.service_tax_amount += tax_amount
						d.customer_service_tax_amount += customer_tax_amount
					else:
						d.other_taxes_and_charges += tax_amount
						d.customer_other_taxes_and_charges += customer_tax_amount


def post_process_items_data(data):
	for i, d in enumerate(data['items']):
		d.idx = i + 1

		data.total_qty += flt(d.qty)

		data.net_total += flt(d.net_amount)
		data.customer_net_total += flt(d.customer_net_amount)

		data.sales_tax_total += flt(d.sales_tax_amount)
		data.customer_sales_tax_total += flt(d.customer_sales_tax_amount)

		data.service_tax_total += flt(d.service_tax_amount)
		data.customer_service_tax_total += flt(d.customer_service_tax_amount)

		data.other_taxes_and_charges += flt(d.other_taxes_and_charges)
		data.customer_other_taxes_and_charges += flt(d.customer_other_taxes_and_charges)

		for tax_account, tax_amount in d.taxes.items():
			data.taxes.setdefault(tax_account, 0)
			data.taxes[tax_account] += tax_amount
		for tax_account, tax_amount in d.customer_taxes.items():
			data.customer_taxes.setdefault(tax_account, 0)
			data.customer_taxes[tax_account] += tax_amount


def get_totals_data(items_dataset, company):
	totals_data = frappe._dict({
		'taxes': {},
		'customer_taxes': {},

		'sales_tax_total': 0,
		'customer_sales_tax_total': 0,

		'service_tax_total': 0,
		'customer_service_tax_total': 0,

		'other_taxes_and_charges': 0,
		'customer_other_taxes_and_charges': 0,

		'total_taxes_and_charges': 0,
		'customer_total_taxes_and_charges': 0,

		'net_total': 0,
		'customer_net_total': 0,

		'grand_total': 0,
		'customer_grand_total': 0,
	})
	for data in items_dataset:
		totals_data.net_total += flt(data.net_total)
		totals_data.customer_net_total += flt(data.customer_net_total)

		totals_data.sales_tax_total += flt(data.sales_tax_total)
		totals_data.customer_sales_tax_total += flt(data.customer_sales_tax_total)

		totals_data.service_tax_total += flt(data.service_tax_total)
		totals_data.customer_service_tax_total += flt(data.customer_service_tax_total)

		totals_data.other_taxes_and_charges += flt(data.other_taxes_and_charges)
		totals_data.customer_other_taxes_and_charges += flt(data.customer_other_taxes_and_charges)

		for tax_account, tax_amount in data.taxes.items():
			totals_data.taxes.setdefault(tax_account, 0)
			totals_data.taxes[tax_account] += tax_amount
			totals_data.total_taxes_and_charges += tax_amount

		for tax_account, tax_amount in data.customer_taxes.items():
			totals_data.customer_taxes.setdefault(tax_account, 0)
			totals_data.customer_taxes[tax_account] += tax_amount
			totals_data.customer_total_taxes_and_charges += tax_amount

	totals_data.grand_total += totals_data.net_total + totals_data.total_taxes_and_charges
	totals_data.customer_grand_total += totals_data.customer_net_total + totals_data.customer_total_taxes_and_charges

	# Round Grand Totals
	grand_total_precision = get_field_precision(frappe.get_meta("Sales Invoice").get_field("grand_total"),
		currency=frappe.get_cached_value('Company', company, "default_currency"))
	totals_data.grand_total = flt(totals_data.grand_total, grand_total_precision)
	totals_data.customer_grand_total = flt(totals_data.customer_grand_total, grand_total_precision)

	return totals_data


def get_timeline_data(doctype, name):
	'''Return timeline for attendance'''
	return dict(frappe.db.sql('''select unix_timestamp(from_time), count(*)
		from `tabTimesheet Detail` where project=%s
			and from_time > date_sub(curdate(), interval 1 year)
			and docstatus < 2
			group by date(from_time)''', name))


def get_project_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"):
	return frappe.db.sql('''select distinct project.*
		from tabProject project, `tabProject User` project_user
		where
			(project_user.user = %(user)s
			and project_user.parent = project.name)
			or project.owner = %(user)s
			order by project.modified desc
			limit {0}, {1}
		'''.format(limit_start, limit_page_length),
						 {'user': frappe.session.user},
						 as_dict=True,
						 update={'doctype': 'Project'})


def get_list_context(context=None):
	return {
		"show_sidebar": True,
		"show_search": True,
		'no_breadcrumbs': True,
		"title": _("Projects"),
		"get_list": get_project_list,
		"row_template": "templates/includes/projects/project_row.html"
	}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_users_for_project(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	return frappe.db.sql("""select name, concat_ws(' ', first_name, middle_name, last_name)
		from `tabUser`
		where enabled=1
			and name not in ("Guest", "Administrator")
			and ({key} like %(txt)s
				or full_name like %(txt)s)
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, full_name), locate(%(_txt)s, full_name), 99999),
			idx desc,
			name, full_name
		limit %(start)s, %(page_len)s""".format(**{
		'key': searchfield,
		'fcond': get_filters_cond(doctype, filters, conditions),
		'mcond': get_match_cond(doctype)
	}), {
							 'txt': "%%%s%%" % txt,
							 '_txt': txt.replace("%", ""),
							 'start': start,
							 'page_len': page_len
						 })


@frappe.whitelist()
def get_cost_center_name(project):
	return frappe.db.get_value("Project", project, "cost_center")


def hourly_reminder():
	fields = ["from_time", "to_time"]
	projects = get_projects_for_collect_progress("Hourly", fields)

	for project in projects:
		if (get_time(nowtime()) >= get_time(project.from_time) or
			get_time(nowtime()) <= get_time(project.to_time)):
			send_project_update_email_to_users(project.name)


def project_status_update_reminder():
	daily_reminder()
	twice_daily_reminder()
	weekly_reminder()


def daily_reminder():
	fields = ["daily_time_to_send"]
	projects =  get_projects_for_collect_progress("Daily", fields)

	for project in projects:
		if allow_to_make_project_update(project.name, project.get("daily_time_to_send"), "Daily"):
			send_project_update_email_to_users(project.name)


def twice_daily_reminder():
	fields = ["first_email", "second_email"]
	projects =  get_projects_for_collect_progress("Twice Daily", fields)
	fields.remove("name")

	for project in projects:
		for d in fields:
			if allow_to_make_project_update(project.name, project.get(d), "Twicely"):
				send_project_update_email_to_users(project.name)


def weekly_reminder():
	fields = ["day_to_send", "weekly_time_to_send"]
	projects =  get_projects_for_collect_progress("Weekly", fields)

	current_day = get_datetime().strftime("%A")
	for project in projects:
		if current_day != project.day_to_send:
			continue

		if allow_to_make_project_update(project.name, project.get("weekly_time_to_send"), "Weekly"):
			send_project_update_email_to_users(project.name)


def allow_to_make_project_update(project, time, frequency):
	data = frappe.db.sql(""" SELECT name from `tabProject Update`
		WHERE project = %s and date = %s """, (project, today()))

	# len(data) > 1 condition is checked for twicely frequency
	if data and (frequency in ['Daily', 'Weekly'] or len(data) > 1):
		return False

	if get_time(nowtime()) >= get_time(time):
		return True


@frappe.whitelist()
def create_duplicate_project(prev_doc, project_name):
	''' Create duplicate project based on the old project '''
	import json
	prev_doc = json.loads(prev_doc)

	if project_name == prev_doc.get('name'):
		frappe.throw(_("Use a name that is different from previous project name"))

	# change the copied doc name to new project name
	project = frappe.copy_doc(prev_doc)
	project.name = project_name
	project.project_template = ''
	project.project_name = project_name
	project.insert()

	# fetch all the task linked with the old project
	task_list = frappe.get_all("Task", filters={
		'project': prev_doc.get('name')
	}, fields=['name'])

	# Create duplicate task for all the task
	for task in task_list:
		task = frappe.get_doc('Task', task)
		new_task = frappe.copy_doc(task)
		new_task.project = project.name
		new_task.insert()

	project.db_set('project_template', prev_doc.get('project_template'))


def get_projects_for_collect_progress(frequency, fields):
	fields.extend(["name"])

	return frappe.get_all("Project", fields = fields,
		filters = {'collect_progress': 1, 'frequency': frequency, 'status': 'Open'})


def send_project_update_email_to_users(project):
	doc = frappe.get_doc('Project', project)

	if is_holiday(doc.holiday_list) or not doc.users: return

	project_update = frappe.get_doc({
		"doctype" : "Project Update",
		"project" : project,
		"sent": 0,
		"date": today(),
		"time": nowtime(),
		"naming_series": "UPDATE-.project.-.YY.MM.DD.-",
	}).insert()

	subject = "For project %s, update your status" % (project)

	incoming_email_account = frappe.db.get_value('Email Account',
		dict(enable_incoming=1, default_incoming=1), 'email_id')

	frappe.sendmail(recipients=get_users_email(doc),
		message=doc.message,
		subject=_(subject),
		reference_doctype=project_update.doctype,
		reference_name=project_update.name,
		reply_to=incoming_email_account
	)


def collect_project_status():
	for data in frappe.get_all("Project Update",
		{'date': today(), 'sent': 0}):
		replies = frappe.get_all('Communication',
			fields=['content', 'text_content', 'sender'],
			filters=dict(reference_doctype="Project Update",
				reference_name=data.name,
				communication_type='Communication',
				sent_or_received='Received'),
			order_by='creation asc')

		for d in replies:
			doc = frappe.get_doc("Project Update", data.name)
			user_data = frappe.db.get_values("User", {"email": d.sender},
				["full_name", "user_image", "name"], as_dict=True)[0]

			doc.append("users", {
				'user': user_data.name,
				'full_name': user_data.full_name,
				'image': user_data.user_image,
				'project_status': frappe.utils.md_to_html(
					EmailReplyParser.parse_reply(d.text_content) or d.content
				)
			})

			doc.save(ignore_permissions=True)


def send_project_status_email_to_users():
	yesterday = add_days(today(), -1)

	for d in frappe.get_all("Project Update",
		{'date': yesterday, 'sent': 0}):
		doc = frappe.get_doc("Project Update", d.name)

		project_doc = frappe.get_doc('Project', doc.project)

		args = {
			"users": doc.users,
			"title": _("Project Summary for {0}").format(yesterday)
		}

		frappe.sendmail(recipients=get_users_email(project_doc),
			template='daily_project_summary',
			args=args,
			subject=_("Daily Project Summary for {0}").format(d.name),
			reference_doctype="Project Update",
			reference_name=d.name)

		doc.db_set('sent', 1)


@frappe.whitelist()
def create_kanban_board_if_not_exists(project):
	from frappe.desk.doctype.kanban_board.kanban_board import quick_kanban_board

	if not frappe.db.exists('Kanban Board', project):
		quick_kanban_board('Task', project, 'status')

	return True


@frappe.whitelist()
def set_project_ready_to_close(project):
	project = frappe.get_doc('Project', project)
	project.check_permission('write')

	project.set_ready_to_close(update=True)
	project.set_status(update=True)
	project.update_vehicle_booking_order_pdi_status()
	project.notify_update()


@frappe.whitelist()
def reopen_project_status(project):
	project = frappe.get_doc('Project', project)
	project.check_permission('write')

	project.reopen_status(update=True)
	project.set_status(update=True, reset=True)
	project.update_vehicle_booking_order_pdi_status()
	project.notify_update()


@frappe.whitelist()
def set_project_status(project, project_status):
	project = frappe.get_doc('Project', project)
	project.check_permission('write')

	project.set_status(status=project_status)
	project.save()

	project.update_vehicle_booking_order_pdi_status()


@frappe.whitelist()
def get_customer_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	customer = frappe._dict()
	if args.customer:
		customer = frappe.get_cached_doc("Customer", args.customer)

	out.customer_name = customer.customer_name

	# Tax IDs
	out.tax_id = customer.tax_id
	out.tax_cnic = customer.tax_cnic
	out.tax_strn = customer.tax_strn
	out.tax_status = customer.tax_status

	# Customer Address
	out.customer_address = args.customer_address
	if not out.customer_address and customer.name:
		out.customer_address = get_default_address("Customer", customer.name)

	out.address_display = get_address_display(out.customer_address)

	# Contact
	out.contact_person = args.contact_person
	if not out.contact_person and customer.name:
		out.contact_person = get_default_contact("Customer", customer.name)

	out.update(get_contact_details(out.contact_person))

	out.secondary_contact_person = args.secondary_contact_person
	secondary_contact_details = get_contact_details(out.secondary_contact_person)
	secondary_contact_details = {"secondary_" + k: v for k, v in secondary_contact_details.items()}
	out.update(secondary_contact_details)

	out.contact_nos = get_all_contact_nos("Customer", customer.name)

	return out


@frappe.whitelist()
def get_project_details(project, doctype):
	if isinstance(project, string_types):
		project = frappe.get_doc("Project", project)

	sales_doctypes = ['Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice']

	out = {}
	fieldnames = [
		'company',
		'customer', 'bill_to', 'vehicle_owner',
		'contact_person', 'contact_mobile', 'contact_phone',
		'applies_to_item', 'applies_to_vehicle',
		'vehicle_chassis_no', 'vehicle_engine_no',
		'vehicle_license_plate', 'vehicle_unregistered',
		'vehicle_last_odometer',
		'service_advisor', 'service_manager',
		'insurance_company', 'insurance_loss_no', 'insurance_policy_no',
		'insurance_surveyor', 'insurance_surveyor_company',
		'has_stin', 'default_depreciation_percentage',
		'campaign'
	]
	sales_only_fields = ['customer', 'bill_to', 'vehicle_owner', 'has_stin', 'default_depreciation_percentage',
		'contact_person', 'contact_mobile', 'contact_phone']

	for f in fieldnames:
		if f in sales_only_fields and doctype not in sales_doctypes:
			continue
		if f in ['customer', 'bill_to'] and not project.get(f):
			continue

		out[f] = project.get(f)

		if doctype == "Quotation" and f == 'customer':
			out['quotation_to'] = 'Customer'
			out['party_name'] = project.get(f)

	out['project_reference_no'] = project.get('reference_no')

	return out


@frappe.whitelist()
def make_against_project(project_name, dt):
	project = frappe.get_doc("Project", project_name)
	doc = frappe.new_doc(dt)

	if doc.meta.has_field('company'):
		doc.company = project.company
	if doc.meta.has_field('project'):
		doc.project = project_name

	# Set customer
	if project.customer:
		if doc.meta.has_field('customer'):
			doc.customer = project.customer
			doc.update(get_fetch_values(doc.doctype, 'customer', project.customer))
		elif dt == 'Quotation':
			doc.quotation_to = 'Customer'
			doc.party_name = project.customer
			doc.update(get_fetch_values(doc.doctype, 'party_name', project.customer))

	if project.applies_to_item:
		if doc.meta.has_field('item_code'):
			doc.item_code = project.applies_to_item
			doc.update(get_fetch_values(doc.doctype, 'item_code', project.applies_to_item))

			if doc.meta.has_field('serial_no'):
				doc.serial_no = project.serial_no
				doc.update(get_fetch_values(doc.doctype, 'serial_no', project.serial_no))
		else:
			child = doc.append("purposes" if dt == "Maintenance Visit" else "items", {
				"item_code": project.applies_to_item,
				"serial_no": project.serial_no
			})
			child.update(get_fetch_values(child.doctype, 'item_code', project.applies_to_item))
			if child.meta.has_field('serial_no'):
				child.update(get_fetch_values(child.doctype, 'serial_no', project.serial_no))

	doc.run_method("set_missing_values")
	doc.run_method("calculate_taxes_and_totals")
	return doc


@frappe.whitelist()
def make_sales_invoice(project_name, target_doc=None, depreciation_type=None, claim_billing=None):
	from erpnext.controllers.queries import _get_sales_orders_to_be_billed, _get_delivery_notes_to_be_billed
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice as invoice_from_delivery_note
	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice as invoice_from_sales_order

	if frappe.flags.args and claim_billing is None:
		claim_billing = cint(frappe.flags.args.claim_billing)

	project = frappe.get_doc("Project", project_name)
	project_details = get_project_details(project, "Sales Invoice")

	# Create Sales Invoice
	if target_doc and isinstance(target_doc, string_types):
		target_doc = json.loads(target_doc)

	if target_doc:
		target_doc = frappe.get_doc(target_doc)
	else:
		target_doc = frappe.new_doc("Sales Invoice")

	# Set Project Details
	if not claim_billing:
		target_doc.company = project.company
		target_doc.project = project.name

		for k, v in project_details.items():
			if target_doc.meta.has_field(k):
				target_doc.set(k, v)

	filters = {"project": project.name}
	if project.company:
		filters['company'] = project.company

	# Get Delivery Notes
	delivery_note_filters = filters.copy()
	delivery_note_filters['is_return'] = 0
	delivery_notes = _get_delivery_notes_to_be_billed(filters=delivery_note_filters)
	for d in delivery_notes:
		target_doc = invoice_from_delivery_note(d.name, target_doc=target_doc, only_items=claim_billing)

	# Get Sales Orders
	sales_order_filters = filters.copy()
	sales_orders = _get_sales_orders_to_be_billed(filters=sales_order_filters)
	for d in sales_orders:
		target_doc = invoice_from_sales_order(d.name, target_doc=target_doc, only_items=claim_billing)

	if not claim_billing:
		# Remove Taxes (so they are reloaded)
		target_doc.taxes_and_charges = None
		target_doc.taxes = []

		# Set Project Details
		for k, v in project_details.items():
			if target_doc.meta.has_field(k):
				target_doc.set(k, v)

		# Depreciation billing case
		if project.default_depreciation_percentage or project.non_standard_depreciation and depreciation_type:
			target_doc.depreciation_type = depreciation_type
			if depreciation_type == "Depreciation Amount Only":
				target_doc.bill_to = target_doc.customer
			elif depreciation_type == "After Depreciation Amount":
				if not project.bill_to and project.insurance_company:
					target_doc.bill_to = project.insurance_company

		# Cash or credit
		if depreciation_type != 'After Depreciation Amount':
			target_doc.is_pos = project.cash_billing

		# Do not copy contact person and address if invoice billing customer is not project customer
		target_billing_customer = target_doc.bill_to or target_doc.customer
		if target_billing_customer != project.customer:
			target_doc.contact_person = None
			target_doc.customer_address = None

		# Insurance Company Fetch Values
		target_doc.update(get_fetch_values(target_doc.doctype, 'insurance_company', target_doc.insurance_company))

	# Missing Values and Forced Values
	target_doc.run_method("set_missing_values")

	if not claim_billing:
		# Set Depreciation Rates
		set_depreciation_in_invoice_items(target_doc.get('items'), project)

		# Tax Table
		target_doc.run_method("append_taxes_from_master")

	# Calculate Taxes and Totals
	target_doc.run_method("calculate_taxes_and_totals")

	# Check Undelivered Sales Order Stock Items
	if not cint(project.get('allow_billing_undelivered_sales_orders')):
		undelivered_sales_orders = []
		has_undelivered_items = False
		for d in target_doc.items:
			if d.is_stock_item and not d.delivery_note and (not claim_billing or d.project == project.name):
				has_undelivered_items = True
				if d.sales_order and d.sales_order not in undelivered_sales_orders:
					undelivered_sales_orders.append(d.sales_order)

		if has_undelivered_items:
			undelivered_sales_orders_txt = [frappe.utils.get_link_to_form("Sales Order", so) for so in undelivered_sales_orders]
			undelivered_sales_orders_txt = ", ".join(undelivered_sales_orders_txt)
			if undelivered_sales_orders_txt:
				undelivered_sales_orders_txt = "<br><br>" + undelivered_sales_orders_txt

			frappe.throw(_("{0} has Sales Orders with undelivered stock items. "
				"If you want to bill undelivered stock items, please confirm billing amount and check "
				"<b>'Allow Billing of Undelivered Materials'</b>{1}")
				.format(frappe.get_desk_link("Project", project.name), undelivered_sales_orders_txt),
				title=_("Undelivered Sales Orders"))

	return target_doc


@frappe.whitelist()
def get_delivery_note(project_name):
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

	project = frappe.get_doc("Project", project_name)
	project_details = get_project_details(project, "Delivery Note")

	# Create Sales Invoice
	target_doc = frappe.new_doc("Delivery Note")
	target_doc.company = project.company
	target_doc.project = project.name

	# Set Project Details
	for k, v in project_details.items():
		if target_doc.meta.has_field(k):
			target_doc.set(k, v)

	# Get Sales Orders
	sales_order_filters = {
		"docstatus": 1,
		"status": ["not in", ["Closed", "On Hold"]],
		"per_delivered": ["<", 99.99],
		"project": project.name,
		"company": project.company,
		"skip_delivery_note": 0,
	}
	sales_orders = frappe.get_all("Sales Order", filters=sales_order_filters)
	for d in sales_orders:
		target_doc = make_delivery_note(d.name, target_doc=target_doc)

	# Remove Taxes (so they are reloaded)
	target_doc.taxes_and_charges = None
	target_doc.taxes = []

	# Set Project Details
	for k, v in project_details.items():
		if target_doc.meta.has_field(k):
			target_doc.set(k, v)

	# Missing Values and Forced Values
	target_doc.run_method("set_missing_values")
	target_doc.run_method("append_taxes_from_master")
	target_doc.run_method("calculate_taxes_and_totals")

	return target_doc


@frappe.whitelist()
def get_sales_order(project_name, items_type=None):
	from erpnext.projects.doctype.project_template.project_template import add_project_template_items

	project = frappe.get_doc("Project", project_name)
	project_details = get_project_details(project, "Sales Order")

	# Create Sales Order
	target_doc = frappe.new_doc("Sales Order")
	target_doc.company = project.company
	target_doc.project = project.name
	target_doc.delivery_date = project.expected_delivery_date

	sales_order_print_heading = frappe.get_cached_value("Projects Settings", None, "sales_order_print_heading")
	if sales_order_print_heading:
		target_doc.select_print_heading = sales_order_print_heading

	# Set Project Details
	for k, v in project_details.items():
		if target_doc.meta.has_field(k):
			target_doc.set(k, v)

	# Get Project Template Items
	for d in project.project_templates:
		if not d.get('sales_order'):
			target_doc = add_project_template_items(target_doc, d.project_template, project.applies_to_item,
				check_duplicate=False, project_template_detail=d, items_type=items_type)

	# Remove already ordered items
	project_template_ordered_set = get_project_template_ordered_set(project)
	to_remove = []
	for d in target_doc.get('items'):
		is_stock_item = 0
		if d.item_code:
			is_stock_item = cint(frappe.get_cached_value("Item", d.item_code, 'is_stock_item'))

		if d.project_template_detail and (d.project_template_detail, is_stock_item) in project_template_ordered_set:
			to_remove.append(d)

	for d in to_remove:
		target_doc.remove(d)
	for i, d in enumerate(target_doc.items):
		d.idx = i + 1

	# Missing Values and Forced Values
	target_doc.run_method("set_missing_values")
	target_doc.run_method("append_taxes_from_master")
	target_doc.run_method("calculate_taxes_and_totals")

	return target_doc


def get_project_template_ordered_set(project):
	project_template_ordered_set = []

	project_template_details = [d.name for d in project.project_templates]
	if project_template_details:
		project_template_ordered_set = frappe.db.sql("""
			select distinct item.project_template_detail, item.is_stock_item
			from `tabSales Order Item` item
			inner join `tabSales Order` so on so.name = item.parent
			where so.docstatus = 1 and so.project = %s and item.project_template_detail in %s
		""", (project.name, project_template_details))

	return project_template_ordered_set


@frappe.whitelist()
def get_vehicle_service_receipt(project):
	doc = frappe.get_doc("Project", project)
	check_if_doc_exists("Vehicle Service Receipt", doc.name, {'docstatus': 0})
	target = frappe.new_doc("Vehicle Service Receipt")
	set_vehicle_transaction_values(doc, target)
	target.run_method("set_missing_values")
	return target


@frappe.whitelist()
def get_vehicle_gate_pass(project, sales_invoice=None):
	doc = frappe.get_doc("Project", project)
	check_if_doc_exists("Vehicle Gate Pass", doc.name, {'docstatus': 0})
	target = frappe.new_doc("Vehicle Gate Pass")
	set_vehicle_transaction_values(doc, target)

	if sales_invoice:
		target.sales_invoice = sales_invoice
	else:
		sales_invoice = doc.get_invoice_for_vehicle_gate_pass()
		if sales_invoice:
			target.sales_invoice = sales_invoice

	target.run_method("set_missing_values")
	return target


def set_vehicle_transaction_values(source, target):
	if not source.applies_to_vehicle:
		frappe.throw(_("Please set Vehicle first"))

	target.company = source.company
	target.project = source.name
	target.item_code = source.applies_to_item
	target.vehicle = source.applies_to_vehicle


def check_if_doc_exists(doctype, project, filters=None):
	filter_args = filters or {}
	filters = {"project": project, "docstatus": ["<", 2]}
	filters.update(filter_args)

	existing = frappe.db.get_value(doctype, filters)
	if existing:
		frappe.throw(_("{0} already exists").format(frappe.get_desk_link(doctype, existing)))


def set_depreciation_in_invoice_items(items_list, project):
	non_standard_depreciation_items = {}
	for d in project.non_standard_depreciation:
		if d.depreciation_item_code:
			non_standard_depreciation_items[d.depreciation_item_code] = flt(d.depreciation_percentage)

	materials_item_groups = project.get_item_groups_subtree(project.materials_item_group)
	for d in items_list:
		if d.is_stock_item or d.item_group in materials_item_groups:
			if not flt(d.depreciation_percentage):
				if d.item_code in non_standard_depreciation_items:
					d.depreciation_percentage = non_standard_depreciation_items[d.item_code]
				else:
					d.depreciation_percentage = flt(project.default_depreciation_percentage)
		else:
			d.depreciation_percentage = 0
