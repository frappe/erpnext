# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from email_reply_parser import EmailReplyParser
from frappe.utils import flt, cint, get_url, cstr, nowtime, get_time, today, get_datetime, add_days, ceil
from erpnext.controllers.queries import get_filters_cond
from frappe.desk.reportview import get_match_cond
from erpnext.hr.doctype.daily_work_summary.daily_work_summary import get_users_email
from erpnext.hr.doctype.holiday_list.holiday_list import is_holiday
from erpnext.stock.get_item_details import get_applies_to_details
from frappe.model.naming import set_name_by_naming_series
from frappe.model.utils import get_fetch_values
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact, get_all_phone_numbers
from erpnext.controllers.status_updater import StatusUpdater
from erpnext.projects.doctype.project_status.project_status import get_auto_project_status, set_manual_project_status,\
	get_valid_manual_project_status_names, is_manual_project_status, validate_project_status_for_transaction
from six import string_types
from erpnext.vehicles.vehicle_checklist import get_default_vehicle_checklist_items, set_missing_checklist
import json


force_applies_to_fields = ("vehicle_chassis_no", "vehicle_engine_no", "vehicle_license_plate", "vehicle_unregistered",
	"vehicle_color", "applies_to_item", "vehicle_owner_name", "vehicle_warranty_no")

force_customer_fields = ("customer_name",
	"tax_id", "tax_cnic", "tax_strn", "tax_status",
	"address_display", "contact_display", "contact_email")

vehicle_change_fields = [
	('change_vehicle_license_plate', 'license_plate'),
	('change_vehicle_warranty_no', 'warranty_no'),
	('change_vehicle_delivery_date', 'delivery_date')
]


class Project(StatusUpdater):
	def __init__(self, *args, **kwargs):
		super(Project, self).__init__(*args, **kwargs)
		self.sales_data = frappe._dict()

	def get_feed(self):
		return '{0}: {1}'.format(_(self.status), frappe.safe_decode(self.project_name or self.name))

	def autoname(self):
		project_naming_by = frappe.defaults.get_global_default('project_naming_by')
		if project_naming_by == 'Project Name':
			self.name = self.project_name
		else:
			set_name_by_naming_series(self, 'project_number')

	def onload(self):
		self.set_onload('activity_summary', frappe.db.sql('''select activity_type,
			sum(hours) as total_hours
			from `tabTimesheet Detail` where project=%s and docstatus < 2 group by activity_type
			order by total_hours desc''', self.name, as_dict=True))

		self.set_onload('default_vehicle_checklist_items', get_default_vehicle_checklist_items('vehicle_checklist'))
		self.set_onload('default_customer_request_checklist_items', get_default_vehicle_checklist_items('customer_request_checklist'))
		self.set_onload('cant_change_fields', self.get_cant_change_fields())
		self.set_onload('valid_manual_project_status_names', get_valid_manual_project_status_names(self))
		self.set_onload('is_manual_project_status', is_manual_project_status(self.project_status))
		self.set_onload('phone_nos', get_all_phone_numbers('Customer', self.customer))

		self.reset_quick_change_fields()
		self.set_missing_checklist()

		self.set_costing()

		self.get_project_sales_data()
		self.set_sales_data_html_onload()

	def before_print(self):
		self.onload()

		self.company_address_doc = erpnext.get_company_address(self)

		self.get_sales_invoice_names()

	def validate(self):
		self.quick_change_master_details()

		self.set_missing_values()

		self.validate_phone_nos()
		self.validate_project_type()
		self.validate_applies_to()
		self.validate_readings()
		self.validate_depreciation()

		self.set_costing()

		self.set_percent_complete()
		self.set_vehicle_status()
		self.set_billing_status()
		self.set_status()

		self.set_title()

		self.validate_cant_change()

		self.send_welcome_email()

	def on_update(self):
		if 'Vehicles' in frappe.get_active_domains():
			self.update_odometer()

	def after_insert(self):
		self.set_project_in_sales_order_and_quotation()

	def set_title(self):
		if self.project_name:
			self.title = self.project_name
		elif self.customer_name or self.customer:
			self.title = self.customer_name or self.customer
		else:
			self.title = self.name

	def set_billing_status(self, update=False, update_modified=False):
		previous_billing_status = self.billing_status

		sales_orders = frappe.get_all("Sales Order", fields=['per_completed'], filters={
			"project": self.name, "docstatus": 1, "status": ['!=', 'Closed']
		})
		delivery_notes = frappe.get_all("Delivery Note", fields=['per_completed'], filters={
			"project": self.name, "docstatus": 1, "status": ['!=', 'Closed']
		})

		has_billables = False
		has_unbilled = False
		for d in sales_orders + delivery_notes:
			has_billables = True
			if d.per_completed < 99.99:
				has_unbilled = True

		sales_invoices = self.get_sales_invoices()
		has_sales_invoice = False
		if sales_invoices:
			has_sales_invoice = True

		if has_billables:
			if has_sales_invoice:
				if has_unbilled:
					self.billing_status = "Partially Billed"
				else:
					self.billing_status = "Fully Billed"
			else:
				self.billing_status = "Not Billed"
		else:
			if has_sales_invoice:
				self.billing_status = "Fully Billed"
			else:
				self.billing_status = "Not Billable"

		if update and self.billing_status != previous_billing_status:
			self.db_set('billing_status', self.billing_status, update_modified=update_modified)

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
		vehicle_received = self.get('vehicle_status') and self.get('vehicle_status') != 'Not Received'
		has_sales_transaction = self.has_sales_transaction()
		return frappe._dict({
			'applies_to_vehicle': vehicle_received,
			'vehicle_workshop': vehicle_received,
			# 'customer': has_sales_transaction,
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

	def validate_project_type(self):
		if self.project_type:
			project_type = frappe.get_cached_doc("Project Type", self.project_type)
			if project_type.campaign_mandatory and not self.get('campaign'):
				frappe.throw(_("Campaign is mandatory for Project Type {0}").format(self.project_type))
			if project_type.previous_project_mandatory and not self.get('previous_project'):
				frappe.throw(_("{0} is mandatory for Project Type {1}")
					.format(self.meta.get_label('previous_project'), self.project_type))

	def validate_phone_nos(self):
		if not self.get('contact_mobile') and self.get('contact_mobile_2'):
			self.contact_mobile = self.contact_mobile_2
			self.contact_mobile_2 = ''
		if self.get('contact_mobile') == self.get('contact_mobile_2'):
			self.contact_mobile_2 = ''

	def set_missing_values(self):
		self.set_customer_details()
		self.set_applies_to_details()
		self.set_missing_checklist()
		self.set_project_template_details()

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

	def validate_readings(self):
		if self.meta.has_field('fuel_level'):
			if flt(self.fuel_level) < 0 or flt(self.fuel_level) > 100:
				frappe.throw(_("Fuel Level must be between 0% and 100%"))
		if self.meta.has_field('keys'):
			if cint(self.keys) < 0:
				frappe.throw(_("No of Keys cannot be negative"))

	def validate_applies_to(self):
		from erpnext.vehicles.utils import format_vehicle_fields
		format_vehicle_fields(self)

		if self.get('applies_to_item') and not self.get('vehicle_workshop'):
			frappe.throw(_("Vehicle Workshop is mandatory when Applies to Item is set"))

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
				if vehicle_change_map.get('license_plate'):
					vehicle_change_map['unregistered'] = 0

				frappe.set_value("Vehicle", self.applies_to_vehicle, vehicle_change_map)

		self.reset_quick_change_fields()

	def reset_quick_change_fields(self):
		for project_field, vehicle_field in vehicle_change_fields:
			if self.meta.has_field(project_field):
				self.set(project_field, None)

	def update_odometer(self):
		from erpnext.vehicles.doctype.vehicle_log.vehicle_log import make_odometer_log
		from erpnext.vehicles.doctype.vehicle.vehicle import get_project_odometer

		if not self.meta.has_field('applies_to_vehicle'):
			return

		if self.get('applies_to_vehicle'):
			reload = False

			odo = get_project_odometer(self.name, self.applies_to_vehicle)
			if not odo.vehicle_first_odometer and self.vehicle_first_odometer:
				make_odometer_log(self.applies_to_vehicle, self.vehicle_first_odometer, project=self.name,
					from_project_update=True)
				reload = True

			if reload:
				odo = get_project_odometer(self.name, self.applies_to_vehicle)
			if self.vehicle_last_odometer and self.vehicle_last_odometer > odo.vehicle_last_odometer:
				make_odometer_log(self.applies_to_vehicle, self.vehicle_last_odometer, project=self.name,
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

	def update_project(self):
		'''Called externally by Task'''
		self.set_percent_complete()
		self.set_costing()
		self.db_update()
		self.notify_update()

	def set_percent_complete(self):
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
				weighted_progress = frappe.db.sql("""select progress, task_weight from tabTask where project=%s""",
					self.name, as_dict=1)
				pct_complete = 0
				for row in weighted_progress:
					pct_complete += row["progress"] * frappe.utils.safe_div(row["task_weight"], weight_sum)
				self.percent_complete = flt(flt(pct_complete), 2)

	def set_sales_data_html_onload(self):
		currency = erpnext.get_company_currency(self.company)

		stock_items_html = frappe.render_template("erpnext/projects/doctype/project/project_items_table.html",
			{"doc": self, "data": self.sales_data.stock_items, "currency": currency,
				"title": _("Materials"), "show_delivery_note": True, "show_uom": True})
		service_items_html = frappe.render_template("erpnext/projects/doctype/project/project_items_table.html",
			{"doc": self, "data": self.sales_data.service_items, "currency": currency,
				"title": _("Services"), "show_delivery_note": False, "show_uom": False})

		sales_summary_html = frappe.render_template("erpnext/projects/doctype/project/project_sales_summary.html",
			{"doc": self, "currency": currency})

		self.set_onload('stock_items_html', stock_items_html)
		self.set_onload('service_items_html', service_items_html)
		self.set_onload('sales_summary_html', sales_summary_html)

	def get_project_sales_data(self):
		self.sales_data.stock_items, self.sales_data.part_items, self.sales_data.lubricant_items = get_stock_items(self.name, self.company)
		self.sales_data.service_items, self.sales_data.labour_items, self.sales_data.sublet_items = get_service_items(self.name, self.company)
		self.sales_data.totals = get_totals_data([self.sales_data.stock_items, self.sales_data.service_items])

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
		self.sales_data.invoices = [d.name for d in invoices]

	def set_costing(self):
		from_time_sheet = frappe.db.sql("""select
			sum(costing_amount) as costing_amount,
			sum(billing_amount) as billing_amount,
			min(from_time) as start_date,
			max(to_time) as end_date,
			sum(hours) as time
			from `tabTimesheet Detail` where project = %s and docstatus = 1""", self.name, as_dict=1)[0]

		from_expense_claim = frappe.db.sql("""select
			sum(sanctioned_amount) as total_sanctioned_amount
			from `tabExpense Claim Detail` where project = %s
			and docstatus = 1""", self.name, as_dict=1)[0]

		self.actual_start_date = from_time_sheet.start_date
		self.actual_end_date = from_time_sheet.end_date

		self.total_costing_amount = from_time_sheet.costing_amount
		self.total_billable_amount = from_time_sheet.billing_amount
		self.actual_time = from_time_sheet.time

		self.total_expense_claim = from_expense_claim.total_sanctioned_amount
		self.update_purchase_costing()
		self.update_sales_amount()
		self.update_billed_amount()
		self.calculate_gross_margin()

	def set_vehicle_status(self, update=False):
		if not self.meta.has_field('vehicle_status'):
			return

		vehicle_service_receipts = None
		vehicle_gate_passes = None

		if self.get('applies_to_vehicle'):
			vehicle_service_receipts = frappe.db.get_all("Vehicle Service Receipt",
				{"project": self.name, "vehicle": self.applies_to_vehicle, "docstatus": 1},
				['name', 'timestamp(posting_date, posting_time) as posting_dt'],
				order_by="posting_date, posting_time, creation")
			vehicle_gate_passes = frappe.db.get_all("Vehicle Gate Pass",
				{"project": self.name, "vehicle": self.applies_to_vehicle, "docstatus": 1},
				['name', 'timestamp(posting_date, posting_time) as posting_dt'],
				order_by="posting_date, posting_time, creation")

		vehicle_service_receipt = frappe._dict()
		vehicle_gate_pass = frappe._dict()

		if vehicle_service_receipts:
			vehicle_service_receipt = vehicle_service_receipts[0]

		if vehicle_gate_passes:
			vehicle_gate_pass = vehicle_gate_passes[-1]

		self.vehicle_received_dt = vehicle_service_receipt.posting_dt
		self.vehicle_delivered_dt = vehicle_gate_pass.posting_dt

		if not vehicle_service_receipt:
			self.vehicle_status = "Not Received"
		elif not vehicle_gate_pass:
			self.vehicle_status = "In Workshop"
		else:
			self.vehicle_status = "Delivered"

		if update:
			self.db_set({
				"vehicle_received_dt": self.vehicle_received_dt,
				"vehicle_delivered_dt": self.vehicle_delivered_dt,
				"vehicle_status": self.vehicle_status,
			})

	def calculate_gross_margin(self):
		expense_amount = (flt(self.total_costing_amount) + flt(self.total_expense_claim)
			+ flt(self.total_purchase_cost) + flt(self.get('total_consumed_material_cost', 0)))

		self.gross_margin = flt(self.total_billed_amount) - expense_amount
		if self.total_billed_amount:
			self.per_gross_margin = (self.gross_margin / flt(self.total_billed_amount)) * 100

	def update_purchase_costing(self):
		total_purchase_cost = frappe.db.sql("""select sum(base_net_amount)
			from `tabPurchase Invoice Item` where project = %s and docstatus=1""", self.name)

		self.total_purchase_cost = total_purchase_cost and total_purchase_cost[0][0] or 0

	def update_sales_amount(self):
		total_sales_amount = frappe.db.sql("""select sum(base_net_total)
			from `tabSales Order` where project = %s and docstatus=1""", self.name)

		self.total_sales_amount = total_sales_amount and total_sales_amount[0][0] or 0

	def update_billed_amount(self):
		total_billed_amount = frappe.db.sql("""select sum(base_net_total)
			from `tabSales Invoice` where project = %s and docstatus=1""", self.name)

		self.total_billed_amount = total_billed_amount and total_billed_amount[0][0] or 0

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


def get_stock_items(project, company):
	dn_data = frappe.db.sql("""
		select p.name as delivery_note, i.sales_order,
			p.posting_date, p.posting_time, i.idx,
			i.item_code, i.item_name, i.description, i.item_group,
			i.qty, i.uom,
			i.net_amount, i.base_net_amount,
			i.net_rate, i.base_net_rate,
			i.item_tax_detail
		from `tabDelivery Note Item` i
		inner join `tabDelivery Note` p on p.name = i.parent
		where p.docstatus = 1 and i.is_stock_item = 1
			and p.project = %s
	""", project, as_dict=1)

	so_data = frappe.db.sql("""
		select p.name as sales_order,
			p.transaction_date, i.idx,
			i.item_code, i.item_name, i.description, i.item_group,
			i.qty - i.delivered_qty as qty, i.qty as ordered_qty, i.uom,
			i.net_amount * (i.qty - i.delivered_qty) / i.qty as net_amount,
			i.base_net_amount * (i.qty - i.delivered_qty) / i.qty as base_net_amount,
			i.net_rate, i.base_net_rate,
			i.item_tax_detail
		from `tabSales Order Item` i
		inner join `tabSales Order` p on p.name = i.parent
		where p.docstatus = 1 and i.is_stock_item = 1 and i.delivered_qty < i.qty and i.qty > 0 and p.status != 'Closed'
			and p.project = %s
	""", project, as_dict=1)

	stock_data = get_items_data_template()
	parts_data = get_items_data_template()
	lubricants_data = get_items_data_template()

	lubricants_item_group = frappe.get_cached_value("Projects Settings", None, "lubricants_item_group")
	lubricants_item_groups = []
	if lubricants_item_group:
		lubricants_item_groups = frappe.get_all("Item Group", {"name": ["subtree of", lubricants_item_group]})
		lubricants_item_groups = [d.name for d in lubricants_item_groups]

	for d in dn_data + so_data:
		stock_data['items'].append(d)

		if d.item_group in lubricants_item_groups:
			lubricants_data['items'].append(d.copy())
		else:
			parts_data['items'].append(d.copy())

	stock_data['items'] = sorted(stock_data['items'], key=lambda d: (cstr(d.posting_date), cstr(d.posting_time), d.idx))
	parts_data['items'] = sorted(parts_data['items'], key=lambda d: (cstr(d.posting_date), cstr(d.posting_time), d.idx))
	lubricants_data['items'] = sorted(lubricants_data['items'], key=lambda d: (cstr(d.posting_date), cstr(d.posting_time), d.idx))

	get_item_taxes(stock_data, company)
	post_process_items_data(stock_data)

	get_item_taxes(parts_data, company)
	post_process_items_data(parts_data)

	get_item_taxes(lubricants_data, company)
	post_process_items_data(lubricants_data)

	return stock_data, parts_data, lubricants_data


def get_service_items(project, company):
	so_data = frappe.db.sql("""
		select p.name as sales_order,
			p.transaction_date,
			i.item_code, i.item_name, i.description, i.item_group,
			i.qty, i.uom,
			i.net_amount, i.base_net_amount,
			i.net_rate, i.base_net_rate,
			i.item_tax_detail
		from `tabSales Order Item` i
		inner join `tabSales Order` p on p.name = i.parent
		where p.docstatus = 1 and i.is_stock_item = 0 and i.is_fixed_asset = 0
			and p.project = %s
		order by p.transaction_date, p.creation, i.idx
	""", project, as_dict=1)

	sinv_data = frappe.db.sql("""
		select p.name as sales_invoice, i.delivery_note, i.sales_order,
			p.posting_date as transaction_date,
			i.item_code, i.item_name, i.description, i.item_group,
			i.qty, i.uom,
			i.net_amount, i.base_net_amount,
			i.net_rate, i.base_net_rate,
			i.item_tax_detail
		from `tabSales Invoice Item` i
		inner join `tabSales Invoice` p on p.name = i.parent
		where p.docstatus = 1 and i.is_stock_item = 0 and i.is_fixed_asset = 0 and ifnull(i.sales_order, '') = ''
			and (p.project = %s or i.project = %s)
		order by p.posting_date, p.creation, i.idx
	""", [project, project], as_dict=1)

	service_data = get_items_data_template()
	labour_data = get_items_data_template()
	sublet_data = get_items_data_template()

	sublet_item_group = frappe.get_cached_value("Projects Settings", None, "sublet_item_group")
	sublet_item_groups = []
	if sublet_item_group:
		sublet_item_groups = frappe.get_all("Item Group", {"name": ["subtree of", sublet_item_group]})
		sublet_item_groups = [d.name for d in sublet_item_groups]

	for d in so_data + sinv_data:
		service_data['items'].append(d)

		if d.item_group in sublet_item_groups:
			sublet_data['items'].append(d.copy())
		else:
			labour_data['items'].append(d.copy())

	get_item_taxes(service_data, company)
	post_process_items_data(service_data)

	get_item_taxes(labour_data, company)
	post_process_items_data(labour_data)

	get_item_taxes(sublet_data, company)
	post_process_items_data(sublet_data)

	return service_data, labour_data, sublet_data


def get_items_data_template():
	return frappe._dict({
		'total_qty': 0,
		'net_total': 0,
		'base_net_total': 0,
		'sales_tax_total': 0,
		'service_tax_total': 0,
		'other_taxes_and_charges': 0,
		'taxes': {},
		'items': [],
	})


def get_item_taxes(data, company):
	sales_tax_account = frappe.get_cached_value('Company', company, "sales_tax_account")
	service_tax_account = frappe.get_cached_value('Company', company, "service_tax_account")

	for d in data['items']:
		d.setdefault('taxes', {})
		d.setdefault('sales_tax_amount', 0)
		d.setdefault('service_tax_amount', 0)
		d.setdefault('other_taxes_and_charges', 0)

		if sales_tax_account or service_tax_account:
			item_tax_detail = json.loads(d.item_tax_detail or '{}')
			for tax_row_name, amount in item_tax_detail.items():
				tax_account = frappe.db.get_value("Sales Taxes and Charges", tax_row_name, 'account_head', cache=1)
				if tax_account:
					tax_amount = flt(amount)
					if flt(d.ordered_qty):
						tax_amount = tax_amount * flt(d.qty) / flt(d.ordered_qty)

					d.taxes.setdefault(tax_account, 0)
					d.taxes[tax_account] += tax_amount

					if tax_account in sales_tax_account:
						d.sales_tax_amount += tax_amount
					elif tax_account in service_tax_account:
						d.service_tax_amount += tax_amount
					else:
						d.other_taxes_and_charges += tax_amount


def post_process_items_data(data):
	for i, d in enumerate(data['items']):
		d.idx = i + 1
		data.total_qty += d.qty
		data.net_total += d.net_amount
		data.base_net_total += d.base_net_amount
		data.sales_tax_total += d.sales_tax_amount
		data.service_tax_total += d.service_tax_amount
		data.other_taxes_and_charges += d.other_taxes_and_charges

		for tax_account, tax_amount in d.taxes.items():
			data.taxes.setdefault(tax_account, 0)
			data.taxes[tax_account] += tax_amount


def get_totals_data(items_dataset):
	totals_data = frappe._dict({
		'taxes': {},
		'sales_tax_total': 0,
		'service_tax_total': 0,
		'other_taxes_and_charges': 0,
		'total_taxes_and_charges': 0,
		'net_total': 0,
		'grand_total': 0,
	})
	for data in items_dataset:
		totals_data.net_total += flt(data.net_total)

		totals_data.sales_tax_total += flt(data.sales_tax_total)
		totals_data.service_tax_total += flt(data.service_tax_total)
		totals_data.other_taxes_and_charges += flt(data.other_taxes_and_charges)

		for tax_account, tax_amount in data.taxes.items():
			totals_data.taxes.setdefault(tax_account, 0)
			totals_data.taxes[tax_account] += tax_amount

			totals_data.total_taxes_and_charges += tax_amount

	totals_data.grand_total += totals_data.net_total + totals_data.total_taxes_and_charges

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
def set_project_released(project, is_released):
	project = frappe.get_doc('Project', project)
	project.check_permission('write')

	is_released = cint(is_released)
	project.is_released = is_released

	if is_released:
		project.status = "Released"
	elif project.status == "Released":
		project.status = "Open"

	project.save()


@frappe.whitelist()
def reopen_project(project):
	project = frappe.get_doc('Project', project)
	project.check_permission('write')

	project.is_released = 0
	project.status = "Open"

	project.set_status(reset=True)
	project.save()


@frappe.whitelist()
def set_project_status(project, project_status):
	project = frappe.get_doc('Project', project)
	project.check_permission('write')

	project.set_status(status=project_status)
	project.save()


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

	out.phone_nos = get_all_phone_numbers("Customer", customer.name)

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
	sales_only_fields = ['customer', 'bill_to', 'vehicle_owner', 'has_stin', 'default_depreciation_percentage']

	for f in fieldnames:
		if f in sales_only_fields and doctype not in sales_doctypes:
			continue
		if f in ['customer', 'bill_to'] and not project.get(f):
			continue

		out[f] = project.get(f)

		if doctype == "Quotation" and f == 'customer':
			out['quotation_to'] = 'Customer'
			out['party_name'] = project.get(f)

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
def get_sales_invoice(project_name, depreciation_type=None):
	from erpnext.controllers.queries import _get_delivery_notes_to_be_billed
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice as invoice_from_delivery_note
	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice as invoice_from_sales_order

	project = frappe.get_doc("Project", project_name)
	project_details = get_project_details(project, "Sales Invoice")

	# Create Sales Invoice
	target_doc = frappe.new_doc("Sales Invoice")
	target_doc.company = project.company
	target_doc.project = project.name

	# Set Project Details
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
		target_doc = invoice_from_delivery_note(d.name, target_doc=target_doc)

	# Get Sales Orders
	sales_order_filters = {
		"docstatus": 1,
		"status": ["not in", ["Closed", "On Hold"]],
		"per_completed": ["<", 99.99],
	}
	sales_order_filters.update(filters)
	sales_orders = frappe.get_all("Sales Order", filters=sales_order_filters)
	for d in sales_orders:
		target_doc = invoice_from_sales_order(d.name, target_doc=target_doc)

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

	if depreciation_type != 'After Depreciation Amount':
		target_doc.is_pos = project.cash_billing

	# Insurance Company Fetch Values
	target_doc.update(get_fetch_values(target_doc.doctype, 'insurance_company', target_doc.insurance_company))

	# Missing Values and Forced Values
	target_doc.run_method("set_missing_values")

	# Set Depreciation Rates
	set_depreciation_in_invoice_items(target_doc, project)

	# Tax Table
	target_doc.run_method("append_taxes_from_master")

	# Calcualte Taxes and Totals
	target_doc.run_method("calculate_taxes_and_totals")

	return target_doc


@frappe.whitelist()
def get_delivery_note(project_name):
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

	project = frappe.get_doc("Project", project_name)
	project_details = get_project_details(project, "Sales Invoice")

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

	# Create Sales Invoice
	target_doc = frappe.new_doc("Sales Order")
	target_doc.company = project.company
	target_doc.project = project.name
	target_doc.delivery_date = project.expected_delivery_date

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
		if d.item_code and d.project_template_detail and (d.item_code, d.project_template_detail) in project_template_ordered_set:
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
			select distinct item.item_code, item.project_template_detail
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


def set_depreciation_in_invoice_items(target_doc, project):
	non_standard_depreciation_items = {}
	for d in project.non_standard_depreciation:
		if d.depreciation_item_code:
			non_standard_depreciation_items[d.depreciation_item_code] = flt(d.depreciation_percentage)

	for d in target_doc.get('items'):
		if d.is_stock_item:
			if not flt(d.depreciation_percentage):
				if d.item_code in non_standard_depreciation_items:
					d.depreciation_percentage = non_standard_depreciation_items[d.item_code]
				else:
					d.depreciation_percentage = flt(project.default_depreciation_percentage)
		else:
			d.depreciation_percentage = 0
