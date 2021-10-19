# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	cstr,
	flt,
	format_datetime,
	formatdate,
	get_datetime,
	get_link_to_form,
	getdate,
	nowdate,
	today,
)

import erpnext
from erpnext.hr.doctype.employee.employee import (
	InactiveEmployeeStatusError,
	get_holiday_list_for_employee,
)


class DuplicateDeclarationError(frappe.ValidationError): pass

def set_employee_name(doc):
	if doc.employee and not doc.employee_name:
		doc.employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")

def update_employee(employee, details, date=None, cancel=False):
	internal_work_history = {}
	for item in details:
		field = frappe.get_meta("Employee").get_field(item.fieldname)
		if not field:
			continue
		fieldtype = field.fieldtype
		new_data = item.new if not cancel else item.current
		if fieldtype == "Date" and new_data:
			new_data = getdate(new_data)
		elif fieldtype =="Datetime" and new_data:
			new_data = get_datetime(new_data)
		setattr(employee, item.fieldname, new_data)
		if item.fieldname in ["department", "designation", "branch"]:
			internal_work_history[item.fieldname] = item.new
	if internal_work_history and not cancel:
		internal_work_history["from_date"] = date
		employee.append("internal_work_history", internal_work_history)
	return employee

@frappe.whitelist()
def get_employee_fields_label():
	fields = []
	for df in frappe.get_meta("Employee").get("fields"):
		if df.fieldname in ["salutation", "user_id", "employee_number", "employment_type",
			"holiday_list", "branch", "department", "designation", "grade",
			"notice_number_of_days", "reports_to", "leave_policy", "company_email"]:
				fields.append({"value": df.fieldname, "label": df.label})
	return fields

@frappe.whitelist()
def get_employee_field_property(employee, fieldname):
	if employee and fieldname:
		field = frappe.get_meta("Employee").get_field(fieldname)
		value = frappe.db.get_value("Employee", employee, fieldname)
		options = field.options
		if field.fieldtype == "Date":
			value = formatdate(value)
		elif field.fieldtype == "Datetime":
			value = format_datetime(value)
		return {
			"value" : value,
			"datatype" : field.fieldtype,
			"label" : field.label,
			"options" : options
		}
	else:
		return False

def validate_dates(doc, from_date, to_date):
	date_of_joining, relieving_date = frappe.db.get_value("Employee", doc.employee, ["date_of_joining", "relieving_date"])
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("To date can not be less than from date"))
	elif getdate(from_date) > getdate(nowdate()):
		frappe.throw(_("Future dates not allowed"))
	elif date_of_joining and getdate(from_date) < getdate(date_of_joining):
		frappe.throw(_("From date can not be less than employee's joining date"))
	elif relieving_date and getdate(to_date) > getdate(relieving_date):
		frappe.throw(_("To date can not greater than employee's relieving date"))

def validate_overlap(doc, from_date, to_date, company = None):
	query = """
		select name
		from `tab{0}`
		where name != %(name)s
		"""
	query += get_doc_condition(doc.doctype)

	if not doc.name:
		# hack! if name is null, it could cause problems with !=
		doc.name = "New "+doc.doctype

	overlap_doc = frappe.db.sql(query.format(doc.doctype),{
			"employee": doc.get("employee"),
			"from_date": from_date,
			"to_date": to_date,
			"name": doc.name,
			"company": company
		}, as_dict = 1)

	if overlap_doc:
		if doc.get("employee"):
			exists_for = doc.employee
		if company:
			exists_for = company
		throw_overlap_error(doc, exists_for, overlap_doc[0].name, from_date, to_date)

def get_doc_condition(doctype):
	if doctype == "Compensatory Leave Request":
		return "and employee = %(employee)s and docstatus < 2 \
		and (work_from_date between %(from_date)s and %(to_date)s \
		or work_end_date between %(from_date)s and %(to_date)s \
		or (work_from_date < %(from_date)s and work_end_date > %(to_date)s))"
	elif doctype == "Leave Period":
		return "and company = %(company)s and (from_date between %(from_date)s and %(to_date)s \
			or to_date between %(from_date)s and %(to_date)s \
			or (from_date < %(from_date)s and to_date > %(to_date)s))"

def throw_overlap_error(doc, exists_for, overlap_doc, from_date, to_date):
	msg = _("A {0} exists between {1} and {2} (").format(doc.doctype,
		formatdate(from_date), formatdate(to_date)) \
		+ """ <b><a href="/app/Form/{0}/{1}">{1}</a></b>""".format(doc.doctype, overlap_doc) \
		+ _(") for {0}").format(exists_for)
	frappe.throw(msg)

def validate_duplicate_exemption_for_payroll_period(doctype, docname, payroll_period, employee):
	existing_record = frappe.db.exists(doctype, {
		"payroll_period": payroll_period,
		"employee": employee,
		'docstatus': ['<', 2],
		'name': ['!=', docname]
	})
	if existing_record:
		frappe.throw(_("{0} already exists for employee {1} and period {2}")
			.format(doctype, employee, payroll_period), DuplicateDeclarationError)

def validate_tax_declaration(declarations):
	subcategories = []
	for d in declarations:
		if d.exemption_sub_category in subcategories:
			frappe.throw(_("More than one selection for {0} not allowed").format(d.exemption_sub_category))
		subcategories.append(d.exemption_sub_category)

def get_total_exemption_amount(declarations):
	exemptions = frappe._dict()
	for d in declarations:
		exemptions.setdefault(d.exemption_category, frappe._dict())
		category_max_amount = exemptions.get(d.exemption_category).max_amount
		if not category_max_amount:
			category_max_amount = frappe.db.get_value("Employee Tax Exemption Category", d.exemption_category, "max_amount")
			exemptions.get(d.exemption_category).max_amount = category_max_amount
		sub_category_exemption_amount = d.max_amount \
			if (d.max_amount and flt(d.amount) > flt(d.max_amount)) else d.amount

		exemptions.get(d.exemption_category).setdefault("total_exemption_amount", 0.0)
		exemptions.get(d.exemption_category).total_exemption_amount += flt(sub_category_exemption_amount)

		if category_max_amount and exemptions.get(d.exemption_category).total_exemption_amount > category_max_amount:
			exemptions.get(d.exemption_category).total_exemption_amount = category_max_amount

	total_exemption_amount = sum([flt(d.total_exemption_amount) for d in exemptions.values()])
	return total_exemption_amount

@frappe.whitelist()
def get_leave_period(from_date, to_date, company):
	leave_period = frappe.db.sql("""
		select name, from_date, to_date
		from `tabLeave Period`
		where company=%(company)s and is_active=1
			and (from_date between %(from_date)s and %(to_date)s
				or to_date between %(from_date)s and %(to_date)s
				or (from_date < %(from_date)s and to_date > %(to_date)s))
	""", {
		"from_date": from_date,
		"to_date": to_date,
		"company": company
	}, as_dict=1)

	if leave_period:
		return leave_period

def generate_leave_encashment():
	''' Generates a draft leave encashment on allocation expiry '''
	from erpnext.hr.doctype.leave_encashment.leave_encashment import create_leave_encashment

	if frappe.db.get_single_value('HR Settings', 'auto_leave_encashment'):
		leave_type = frappe.get_all('Leave Type', filters={'allow_encashment': 1}, fields=['name'])
		leave_type=[l['name'] for l in leave_type]

		leave_allocation = frappe.get_all("Leave Allocation", filters={
			'to_date': add_days(today(), -1),
			'leave_type': ('in', leave_type)
		}, fields=['employee', 'leave_period', 'leave_type', 'to_date', 'total_leaves_allocated', 'new_leaves_allocated'])

		create_leave_encashment(leave_allocation=leave_allocation)

def allocate_earned_leaves():
	'''Allocate earned leaves to Employees'''
	e_leave_types = get_earned_leaves()
	today = getdate()

	for e_leave_type in e_leave_types:

		leave_allocations = get_leave_allocations(today, e_leave_type.name)

		for allocation in leave_allocations:

			if not allocation.leave_policy_assignment and not allocation.leave_policy:
				continue

			leave_policy = allocation.leave_policy if allocation.leave_policy else frappe.db.get_value(
					"Leave Policy Assignment", allocation.leave_policy_assignment, ["leave_policy"])

			annual_allocation = frappe.db.get_value("Leave Policy Detail", filters={
				'parent': leave_policy,
				'leave_type': e_leave_type.name
			}, fieldname=['annual_allocation'])

			from_date=allocation.from_date

			if e_leave_type.based_on_date_of_joining_date:
				from_date  = frappe.db.get_value("Employee", allocation.employee, "date_of_joining")

			if check_effective_date(from_date, today, e_leave_type.earned_leave_frequency, e_leave_type.based_on_date_of_joining_date):
				update_previous_leave_allocation(allocation, annual_allocation, e_leave_type)

def update_previous_leave_allocation(allocation, annual_allocation, e_leave_type):
		earned_leaves = get_monthly_earned_leave(annual_allocation, e_leave_type.earned_leave_frequency, e_leave_type.rounding)

		allocation = frappe.get_doc('Leave Allocation', allocation.name)
		new_allocation = flt(allocation.total_leaves_allocated) + flt(earned_leaves)

		if new_allocation > e_leave_type.max_leaves_allowed and e_leave_type.max_leaves_allowed > 0:
			new_allocation = e_leave_type.max_leaves_allowed

		if new_allocation != allocation.total_leaves_allocated:
			allocation.db_set("total_leaves_allocated", new_allocation, update_modified=False)
			today_date = today()
			create_additional_leave_ledger_entry(allocation, earned_leaves, today_date)

def get_monthly_earned_leave(annual_leaves, frequency, rounding):
	earned_leaves = 0.0
	divide_by_frequency = {"Yearly": 1, "Half-Yearly": 6, "Quarterly": 4, "Monthly": 12}
	if annual_leaves:
		earned_leaves = flt(annual_leaves) / divide_by_frequency[frequency]
		if rounding:
			if rounding == "0.25":
				earned_leaves = round(earned_leaves * 4) / 4
			elif rounding == "0.5":
				earned_leaves = round(earned_leaves * 2) / 2
			else:
				earned_leaves = round(earned_leaves)

	return earned_leaves


def get_leave_allocations(date, leave_type):
	return frappe.db.sql("""select name, employee, from_date, to_date, leave_policy_assignment, leave_policy
		from `tabLeave Allocation`
		where
			%s between from_date and to_date and docstatus=1
			and leave_type=%s""",
	(date, leave_type), as_dict=1)


def get_earned_leaves():
	return frappe.get_all("Leave Type",
		fields=["name", "max_leaves_allowed", "earned_leave_frequency", "rounding", "based_on_date_of_joining"],
		filters={'is_earned_leave' : 1})

def create_additional_leave_ledger_entry(allocation, leaves, date):
	''' Create leave ledger entry for leave types '''
	allocation.new_leaves_allocated = leaves
	allocation.from_date = date
	allocation.unused_leaves = 0
	allocation.create_leave_ledger_entry()

def check_effective_date(from_date, to_date, frequency, based_on_date_of_joining_date):
	import calendar

	from dateutil import relativedelta

	from_date = get_datetime(from_date)
	to_date = get_datetime(to_date)
	rd = relativedelta.relativedelta(to_date, from_date)
	#last day of month
	last_day =  calendar.monthrange(to_date.year, to_date.month)[1]

	if (from_date.day == to_date.day and based_on_date_of_joining_date) or (not based_on_date_of_joining_date and to_date.day == last_day):
		if frequency == "Monthly":
			return True
		elif frequency == "Quarterly" and rd.months % 3:
			return True
		elif frequency == "Half-Yearly" and rd.months % 6:
			return True
		elif frequency == "Yearly" and rd.months % 12:
			return True

	if frappe.flags.in_test:
		return True

	return False


def get_salary_assignment(employee, date):
	assignment = frappe.db.sql("""
		select * from `tabSalary Structure Assignment`
		where employee=%(employee)s
		and docstatus = 1
		and %(on_date)s >= from_date order by from_date desc limit 1""", {
			'employee': employee,
			'on_date': date,
		}, as_dict=1)
	return assignment[0] if assignment else None

def get_sal_slip_total_benefit_given(employee, payroll_period, component=False):
	total_given_benefit_amount = 0
	query = """
	select sum(sd.amount) as 'total_amount'
	from `tabSalary Slip` ss, `tabSalary Detail` sd
	where ss.employee=%(employee)s
	and ss.docstatus = 1 and ss.name = sd.parent
	and sd.is_flexible_benefit = 1 and sd.parentfield = "earnings"
	and sd.parenttype = "Salary Slip"
	and (ss.start_date between %(start_date)s and %(end_date)s
		or ss.end_date between %(start_date)s and %(end_date)s
		or (ss.start_date < %(start_date)s and ss.end_date > %(end_date)s))
	"""

	if component:
		query += "and sd.salary_component = %(component)s"

	sum_of_given_benefit = frappe.db.sql(query, {
		'employee': employee,
		'start_date': payroll_period.start_date,
		'end_date': payroll_period.end_date,
		'component': component
	}, as_dict=True)

	if sum_of_given_benefit and flt(sum_of_given_benefit[0].total_amount) > 0:
		total_given_benefit_amount = sum_of_given_benefit[0].total_amount
	return total_given_benefit_amount

def get_holiday_dates_for_employee(employee, start_date, end_date):
	"""return a list of holiday dates for the given employee between start_date and end_date"""
	# return only date
	holidays = get_holidays_for_employee(employee, start_date, end_date)

	return [cstr(h.holiday_date) for h in holidays]


def get_holidays_for_employee(employee, start_date, end_date, raise_exception=True, only_non_weekly=False):
	"""Get Holidays for a given employee

		`employee` (str)
		`start_date` (str or datetime)
		`end_date` (str or datetime)
		`raise_exception` (bool)
		`only_non_weekly` (bool)

		return: list of dicts with `holiday_date` and `description`
	"""
	holiday_list = get_holiday_list_for_employee(employee, raise_exception=raise_exception)

	if not holiday_list:
		return []

	filters = {
		'parent': holiday_list,
		'holiday_date': ('between', [start_date, end_date])
	}

	if only_non_weekly:
		filters['weekly_off'] = False

	holidays = frappe.get_all(
		'Holiday',
		fields=['description', 'holiday_date'],
		filters=filters
	)

	return holidays

@erpnext.allow_regional
def calculate_annual_eligible_hra_exemption(doc):
	# Don't delete this method, used for localization
	# Indian HRA Exemption Calculation
	return {}

@erpnext.allow_regional
def calculate_hra_exemption_for_period(doc):
	# Don't delete this method, used for localization
	# Indian HRA Exemption Calculation
	return {}

def get_previous_claimed_amount(employee, payroll_period, non_pro_rata=False, component=False):
	total_claimed_amount = 0
	query = """
	select sum(claimed_amount) as 'total_amount'
	from `tabEmployee Benefit Claim`
	where employee=%(employee)s
	and docstatus = 1
	and (claim_date between %(start_date)s and %(end_date)s)
	"""
	if non_pro_rata:
		query += "and pay_against_benefit_claim = 1"
	if component:
		query += "and earning_component = %(component)s"

	sum_of_claimed_amount = frappe.db.sql(query, {
		'employee': employee,
		'start_date': payroll_period.start_date,
		'end_date': payroll_period.end_date,
		'component': component
	}, as_dict=True)
	if sum_of_claimed_amount and flt(sum_of_claimed_amount[0].total_amount) > 0:
		total_claimed_amount = sum_of_claimed_amount[0].total_amount
	return total_claimed_amount

def share_doc_with_approver(doc, user):
	# if approver does not have permissions, share
	if not frappe.has_permission(doc=doc, ptype="submit", user=user):
		frappe.share.add(doc.doctype, doc.name, user, submit=1,
			flags={"ignore_share_permission": True})

		frappe.msgprint(_("Shared with the user {0} with {1} access").format(
			user, frappe.bold("submit"), alert=True))

	# remove shared doc if approver changes
	doc_before_save = doc.get_doc_before_save()
	if doc_before_save:
		approvers = {
			"Leave Application": "leave_approver",
			"Expense Claim": "expense_approver",
			"Shift Request": "approver"
		}

		approver = approvers.get(doc.doctype)
		if doc_before_save.get(approver) != doc.get(approver):
			frappe.share.remove(doc.doctype, doc.name, doc_before_save.get(approver))

def validate_active_employee(employee):
	if frappe.db.get_value("Employee", employee, "status") == "Inactive":
		frappe.throw(_("Transactions cannot be created for an Inactive Employee {0}.").format(
			get_link_to_form("Employee", employee)), InactiveEmployeeStatusError)
