# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import frappe
from frappe import _, scrub, throw
from frappe.model.naming import set_name_by_naming_series
from frappe.permissions import (
	add_user_permission,
	get_doc_permissions,
	remove_user_permission,
)
from frappe.utils import cint, cstr, getdate, today, validate_email_address
from frappe.utils.nestedset import NestedSet

from erpnext.utilities.transaction_base import delete_events


class EmployeeUserDisabledError(frappe.ValidationError):
	pass


class InactiveEmployeeStatusError(frappe.ValidationError):
	pass


class Employee(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.setup.doctype.employee_education.employee_education import EmployeeEducation
		from erpnext.setup.doctype.employee_external_work_history.employee_external_work_history import (
			EmployeeExternalWorkHistory,
		)
		from erpnext.setup.doctype.employee_internal_work_history.employee_internal_work_history import (
			EmployeeInternalWorkHistory,
		)

		attendance_device_id: DF.Data | None
		bank_ac_no: DF.Data | None
		bank_name: DF.Data | None
		bio: DF.TextEditor | None
		blood_group: DF.Literal["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
		branch: DF.Link | None
		cell_number: DF.Data | None
		company: DF.Link
		company_email: DF.Data | None
		contract_end_date: DF.Date | None
		create_user_automatically: DF.Check
		create_user_permission: DF.Check
		ctc: DF.Currency
		current_accommodation_type: DF.Literal["", "Rented", "Owned"]
		current_address: DF.SmallText | None
		date_of_birth: DF.Date
		date_of_issue: DF.Date | None
		date_of_joining: DF.Date
		date_of_retirement: DF.Date | None
		department: DF.Link | None
		designation: DF.Link | None
		education: DF.Table[EmployeeEducation]
		emergency_phone_number: DF.Data | None
		employee: DF.Data | None
		employee_name: DF.Data | None
		employee_number: DF.Data | None
		encashment_date: DF.Date | None
		external_work_history: DF.Table[EmployeeExternalWorkHistory]
		family_background: DF.SmallText | None
		feedback: DF.SmallText | None
		final_confirmation_date: DF.Date | None
		first_name: DF.Data
		gender: DF.Link
		health_details: DF.SmallText | None
		held_on: DF.Date | None
		holiday_list: DF.Link | None
		iban: DF.Data | None
		image: DF.AttachImage | None
		internal_work_history: DF.Table[EmployeeInternalWorkHistory]
		last_name: DF.Data | None
		leave_encashed: DF.Literal["", "Yes", "No"]
		lft: DF.Int
		marital_status: DF.Literal["", "Single", "Married", "Divorced", "Widowed"]
		middle_name: DF.Data | None
		naming_series: DF.Literal["HR-EMP-"]
		new_workplace: DF.Data | None
		notice_number_of_days: DF.Int
		old_parent: DF.Data | None
		passport_number: DF.Data | None
		permanent_accommodation_type: DF.Literal["", "Rented", "Owned"]
		permanent_address: DF.SmallText | None
		person_to_be_contacted: DF.Data | None
		personal_email: DF.Data | None
		place_of_issue: DF.Data | None
		prefered_contact_email: DF.Literal["", "Company Email", "Personal Email", "User ID"]
		prefered_email: DF.Data | None
		reason_for_leaving: DF.SmallText | None
		relation: DF.Data | None
		relieving_date: DF.Date | None
		reports_to: DF.Link | None
		resignation_letter_date: DF.Date | None
		rgt: DF.Int
		salary_currency: DF.Link | None
		salary_mode: DF.Literal["", "Bank", "Cash", "Cheque"]
		salutation: DF.Link | None
		scheduled_confirmation_date: DF.Date | None
		status: DF.Literal["Active", "Inactive", "Suspended", "Left"]
		unsubscribed: DF.Check
		user_id: DF.Link | None
		valid_upto: DF.Date | None
	# end: auto-generated types

	nsm_parent_field = "reports_to"

	def autoname(self):
		set_name_by_naming_series(self)
		self.employee = self.name

	def validate(self):
		from erpnext.controllers.status_updater import validate_status

		validate_status(self.status, ["Active", "Inactive", "Suspended", "Left"])

		self.employee = self.name
		self.set_employee_name()
		self.validate_date()
		self.validate_email()
		self.validate_status()
		self.validate_reports_to()
		self.set_preferred_email()
		self.validate_preferred_email()

		if self.user_id:
			self.validate_user_details()
		else:
			existing_user_id = frappe.db.get_value("Employee", self.name, "user_id")
			if existing_user_id:
				user = frappe.get_doc("User", existing_user_id)
				validate_employee_role(user, ignore_emp_check=True)
				user.save(ignore_permissions=True)
				remove_user_permission("Employee", self.name, existing_user_id)

	def after_rename(self, old, new, merge):
		self.db_set("employee", new)

	def set_employee_name(self):
		self.employee_name = " ".join(
			filter(lambda x: x, [self.first_name, self.middle_name, self.last_name])
		)

	def validate_user_details(self):
		if self.user_id:
			data = frappe.db.get_value("User", self.user_id, ["enabled"], as_dict=1)

			if not data:
				self.user_id = None
				return

			self.validate_for_enabled_user_id(data.get("enabled", 0))
			self.validate_duplicate_user_id()

	def validate_auto_user_creation(self):
		if self.create_user_automatically and not (
			self.prefered_email or self.company_email or self.personal_email
		):
			frappe.throw(
				_("Company or Personal Email is mandatory when 'Create User Automatically' is enabled"),
				frappe.MandatoryError,
				title=_("Auto User Creation Error"),
			)

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_update(self):
		self.update_nsm_model()
		frappe.clear_cache()
		if self.user_id:
			self.update_user()
			self.update_user_permissions()
		self.reset_employee_emails_cache()

	def before_insert(self):
		self.validate_auto_user_creation()

	def after_insert(self):
		if not self.create_user_automatically:
			return

		if self.user_id:
			return

		create_user(
			employee=self.name,
			email=self.prefered_email or self.company_email or self.personal_email,
			create_user_permission=self.create_user_permission,
		)

	def update_user_permissions(self):
		if not self.has_value_changed("user_id") and not self.has_value_changed("create_user_permission"):
			return

		employee_user_permission_exists = frappe.db.exists(
			"User Permission", {"allow": "Employee", "for_value": self.name, "user": self.user_id}
		)

		if employee_user_permission_exists and not self.create_user_permission:
			remove_user_permission("Employee", self.name, self.user_id)
			remove_user_permission("Company", self.company, self.user_id)
		elif not employee_user_permission_exists and self.create_user_permission:
			add_user_permission("Employee", self.name, self.user_id)
			add_user_permission("Company", self.company, self.user_id)

	def update_user(self):
		# add employee role if missing
		user = frappe.get_doc("User", self.user_id)
		user.flags.ignore_permissions = True

		if "Employee" not in user.get("roles"):
			user.append_roles("Employee")

		# copy details like Fullname, DOB and Image to User
		if self.employee_name and not (user.first_name and user.last_name):
			employee_name = self.employee_name.split(" ")
			if len(employee_name) >= 3:
				user.last_name = " ".join(employee_name[2:])
				user.middle_name = employee_name[1]
			elif len(employee_name) == 2:
				user.last_name = employee_name[1]

			user.first_name = employee_name[0]

		if self.date_of_birth:
			user.birth_date = self.date_of_birth

		if self.gender:
			user.gender = self.gender

		if self.image:
			if not user.user_image or self.has_value_changed("image"):
				user.user_image = self.image
				try:
					frappe.get_doc(
						{
							"doctype": "File",
							"file_url": self.image,
							"attached_to_doctype": "User",
							"attached_to_name": self.user_id,
						}
					).insert(ignore_if_duplicate=True)
				except frappe.DuplicateEntryError:
					# already exists
					pass

		user.save()

	def validate_date(self):
		if self.date_of_birth and getdate(self.date_of_birth) > getdate(today()):
			throw(_("Date of Birth cannot be greater than today."))

		self.validate_from_to_dates("date_of_birth", "date_of_joining")
		self.validate_from_to_dates("date_of_joining", "date_of_retirement")
		self.validate_from_to_dates("date_of_joining", "relieving_date")
		self.validate_from_to_dates("date_of_joining", "contract_end_date")

	def validate_email(self):
		if self.company_email:
			validate_email_address(self.company_email, True)
		if self.personal_email:
			validate_email_address(self.personal_email, True)

	def set_preferred_email(self):
		preferred_email_field = frappe.scrub(self.prefered_contact_email)
		self.prefered_email = self.get(preferred_email_field) if preferred_email_field else None

	def validate_status(self):
		if self.status == "Left":
			reports_to = frappe.db.get_all(
				"Employee",
				filters={"reports_to": self.name, "status": "Active"},
				fields=["name", "employee_name"],
			)
			if reports_to:
				link_to_employees = [
					frappe.utils.get_link_to_form("Employee", employee.name, label=employee.employee_name)
					for employee in reports_to
				]
				message = _("The following employees are currently still reporting to {0}:").format(
					frappe.bold(self.employee_name)
				)
				message += "<br><br><ul><li>" + "</li><li>".join(link_to_employees)
				message += "</li></ul><br>"
				message += _("Please make sure the employees above report to another Active employee.")
				throw(message, InactiveEmployeeStatusError, _("Cannot Relieve Employee"))
			if not self.relieving_date:
				throw(_("Please enter relieving date."))

	def validate_for_enabled_user_id(self, enabled):
		if enabled is None:
			frappe.throw(_("User {0} does not exist").format(self.user_id))

		if self.status != "Active" and enabled or self.status == "Active" and enabled == 0:
			frappe.set_value("User", self.user_id, "enabled", not enabled)

	def validate_duplicate_user_id(self):
		Employee = frappe.qb.DocType("Employee")
		employee = (
			frappe.qb.from_(Employee)
			.select(Employee.name)
			.where(
				(Employee.user_id == self.user_id)
				& (Employee.status == "Active")
				& (Employee.name != self.name)
			)
		).run()
		if employee:
			throw(
				_("User {0} is already assigned to Employee {1}").format(self.user_id, employee[0][0]),
				frappe.DuplicateEntryError,
			)

	def validate_reports_to(self):
		if self.reports_to == self.name:
			throw(_("Employee cannot report to himself."))

	def on_trash(self):
		self.update_nsm_model()
		delete_events(self.doctype, self.name)

	def validate_preferred_email(self):
		if self.prefered_contact_email and not self.get(scrub(self.prefered_contact_email)):
			frappe.msgprint(_("Please enter {0}").format(self.prefered_contact_email))

	def reset_employee_emails_cache(self):
		prev_doc = self.get_doc_before_save() or {}
		cell_number = cstr(self.get("cell_number"))
		prev_number = cstr(prev_doc.get("cell_number"))
		if cell_number != prev_number or self.get("user_id") != prev_doc.get("user_id"):
			frappe.cache().hdel("employees_with_number", cell_number)
			frappe.cache().hdel("employees_with_number", prev_number)


def validate_employee_role(doc, method=None, ignore_emp_check=False):
	# called via User hook
	if not ignore_emp_check:
		if frappe.db.get_value("Employee", {"user_id": doc.name}):
			return

	user_roles = [d.role for d in doc.get("roles")]
	if "Employee" in user_roles:
		frappe.msgprint(_("User {0}: Removed Employee role as there is no mapped employee.").format(doc.name))
		doc.get("roles").remove(doc.get("roles", {"role": "Employee"})[0])

	if "Employee Self Service" in user_roles:
		frappe.msgprint(
			_("User {0}: Removed Employee Self Service role as there is no mapped employee.").format(doc.name)
		)
		doc.get("roles").remove(doc.get("roles", {"role": "Employee Self Service"})[0])


def get_employee_email(employee_doc):
	return (
		employee_doc.get("user_id") or employee_doc.get("personal_email") or employee_doc.get("company_email")
	)


def get_holiday_list_for_employee(employee, raise_exception=True, as_on=None):
	hrms_override = frappe.get_hooks("employee_holiday_list")

	if hrms_override:
		return frappe.get_attr(hrms_override[-1])(employee, raise_exception, as_on)
	if employee:
		holiday_list, company = frappe.get_cached_value("Employee", employee, ["holiday_list", "company"])
	else:
		holiday_list = ""
		company = frappe.db.get_single_value("Global Defaults", "default_company")

	if not holiday_list:
		holiday_list = frappe.get_cached_value("Company", company, "default_holiday_list")

	if not holiday_list and raise_exception:
		frappe.throw(
			_("Please set a default Holiday List for Employee {0} or Company {1}").format(employee, company)
		)

	return holiday_list


def is_holiday(employee, date=None, raise_exception=True, only_non_weekly=False, with_description=False):
	"""
	Returns True if given Employee has an holiday on the given date
	        :param employee: Employee `name`
	        :param date: Date to check. Will check for today if None
	        :param raise_exception: Raise an exception if no holiday list found, default is True
	        :param only_non_weekly: Check only non-weekly holidays, default is False
	"""

	holiday_list = get_holiday_list_for_employee(employee, raise_exception)
	if not date:
		date = today()

	if not holiday_list:
		return False

	filters = {"parent": holiday_list, "holiday_date": date}
	if only_non_weekly:
		filters["weekly_off"] = False

	holidays = frappe.get_all("Holiday", fields=["description"], filters=filters, pluck="description")

	if with_description:
		return len(holidays) > 0, holidays

	return len(holidays) > 0


@frappe.whitelist()
def deactivate_sales_person(status: str | None = None, employee: str | None = None):
	if status == "Left":
		sales_person = frappe.db.get_value("Sales Person", {"Employee": employee})
		if sales_person:
			frappe.db.set_value("Sales Person", sales_person, "enabled", 0)


@frappe.whitelist()
def create_user(employee: str, email: str | None = None, create_user_permission: int = 0) -> str:
	emp = frappe.get_doc("Employee", employee)
	if emp.user_id:
		frappe.throw(_("Employee {0} already has a linked user").format(emp.name))

	if not email:
		frappe.throw(_("Email is required to create a user"))

	email = validate_email_address(email, True)
	employee_name = emp.employee_name.split(" ")
	first_name = employee_name[0]
	middle_name = last_name = ""

	if len(employee_name) >= 3:
		last_name = " ".join(employee_name[2:])
		middle_name = employee_name[1]
	elif len(employee_name) == 2:
		last_name = employee_name[1]

	user = frappe.new_doc("User")
	user.update(
		{
			"email": email,
			"enabled": 1,
			"first_name": first_name,
			"middle_name": middle_name,
			"last_name": last_name,
			"gender": emp.gender,
			"birth_date": emp.date_of_birth,
			"phone": emp.cell_number,
			"bio": emp.bio,
		}
	)
	emp.db_set("user_id", email)
	user.append_roles("Employee")
	user.insert()

	emp.user_id = user.name
	emp.create_user_permission = cint(create_user_permission)
	emp.save()

	if cint(create_user_permission):
		add_user_permission("Employee", emp.name, user.name)
		add_user_permission("Company", emp.company, user.name)

	return user.name


def get_all_employee_emails(company):
	"""Returns list of employee emails either based on user_id or company_email"""
	employee_list = frappe.get_all(
		"Employee", fields=["name", "employee_name"], filters={"status": "Active", "company": company}
	)
	employee_emails = []
	for employee in employee_list:
		if not employee:
			continue
		user, company_email, personal_email = frappe.db.get_value(
			"Employee", employee, ["user_id", "company_email", "personal_email"]
		)
		email = user or company_email or personal_email
		if email:
			employee_emails.append(email)
	return employee_emails


def get_employee_emails(employee_list):
	"""Returns list of employee emails either based on user_id or company_email"""
	employee_emails = []
	for employee in employee_list:
		if not employee:
			continue
		user, company_email, personal_email = frappe.db.get_value(
			"Employee", employee, ["user_id", "company_email", "personal_email"]
		)
		email = user or company_email or personal_email
		if email:
			employee_emails.append(email)
	return employee_emails


@frappe.whitelist()
def get_children(
	doctype: str,
	parent: str | None = None,
	company: str | None = None,
	is_root: bool = False,
	is_tree: bool = False,
):
	filters = [["status", "=", "Active"]]
	if company and company != "All Companies":
		filters.append(["company", "=", company])

	fields = ["name as value", "employee_name as title"]

	if is_root:
		parent = ""
	if parent and company and parent != company:
		filters.append(["reports_to", "=", parent])
	else:
		filters.append(["reports_to", "=", ""])

	employees = frappe.get_list(doctype, fields=fields, filters=filters, order_by="name")

	for employee in employees:
		is_expandable = frappe.get_all(doctype, filters=[["reports_to", "=", employee.get("value")]])
		employee.expandable = 1 if is_expandable else 0

	return employees


def on_doctype_update():
	frappe.db.add_index("Employee", ["lft", "rgt"])


def has_user_permission_for_employee(user_name, employee_name):
	return frappe.db.exists(
		{
			"doctype": "User Permission",
			"user": user_name,
			"allow": "Employee",
			"for_value": employee_name,
		}
	)


def has_upload_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user
	if get_doc_permissions(doc, user=user, ptype=ptype).get(ptype):
		return True
	return doc.user_id == user


@frappe.whitelist()
def get_contact_details(employee: str) -> dict:
	"""
	Returns basic contact details for the given employee.

	Email is selected based on the following priority:
	1. Prefered Email
	2. Company Email
	3. Personal Email
	4. User ID
	"""
	if not employee:
		frappe.throw(msg=_("Employee is required"), title=_("Missing Parameter"))

	frappe.has_permission("Employee", "read", employee, throw=True)

	return _get_contact_details(employee)


def _get_contact_details(employee: str) -> dict:
	contact_data = frappe.db.get_value(
		"Employee",
		employee,
		[
			"employee_name",
			"prefered_email",
			"company_email",
			"personal_email",
			"user_id",
			"cell_number",
			"designation",
			"department",
		],
		as_dict=True,
	)

	if not contact_data:
		frappe.throw(msg=_("Employee {0} not found").format(employee), title=_("Not Found"))

	# Email with priority
	employee_email = (
		contact_data.get("prefered_email")
		or contact_data.get("company_email")
		or contact_data.get("personal_email")
		or contact_data.get("user_id")
	)

	return {
		"contact_display": contact_data.get("employee_name"),
		"contact_email": employee_email,
		"contact_mobile": contact_data.get("cell_number"),
		"contact_designation": contact_data.get("designation"),
		"contact_department": contact_data.get("department"),
	}
