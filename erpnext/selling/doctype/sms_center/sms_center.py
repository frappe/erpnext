# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.model.document import Document
from frappe.query_builder import functions as fn
from frappe.utils import cstr


class SMSCenter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		branch: DF.Link | None
		customer: DF.Link | None
		department: DF.Link | None
		message: DF.Text
		receiver_list: DF.Code | None
		sales_partner: DF.Link | None
		send_to: DF.Literal[
			"",
			"All Contact",
			"All Customer Contact",
			"All Supplier Contact",
			"All Sales Partner Contact",
			"All Lead (Open)",
			"All Employee (Active)",
			"All Sales Person",
		]
		supplier: DF.Link | None
		total_characters: DF.Int
		total_messages: DF.Int
	# end: auto-generated types

	@frappe.whitelist()
	def create_receiver_list(self):
		query = None

		if self.send_to == "":
			return

		if self.send_to in [
			"All Contact",
			"All Customer Contact",
			"All Supplier Contact",
			"All Sales Partner Contact",
		]:
			query = self.get_contact_query_for_all_contacts()

		elif self.send_to == "All Lead (Open)":
			query = self.get_contact_query_for_all_open_leads()

		elif self.send_to == "All Employee (Active)":
			query = self.get_contact_query_for_all_active_employee()

		elif self.send_to == "All Sales Person":
			query = self.get_contact_query_for_all_sales_person()

		rec = query.run(as_list=1)

		rec_list = ""
		for d in rec:
			rec_list += d[0] + " - " + d[1] + "\n"
		self.receiver_list = rec_list

	def get_contact_query_for_all_contacts(self):
		Contact = frappe.qb.DocType("Contact")
		DynamicLink = frappe.qb.DocType("Dynamic Link")
		query = (
			frappe.qb.from_(Contact)
			.join(DynamicLink)
			.on(DynamicLink.parent == Contact.name)
			.select(
				fn.Concat(fn.IfNull(Contact.first_name, ""), " ", fn.IfNull(Contact.last_name, "")),
				Contact.mobile_no,
			)
			.where((fn.IfNull(Contact.mobile_no, "") != "") & (Contact.docstatus != 2))
		)

		if self.send_to == "All Customer Contact":
			query = query.where(DynamicLink.link_doctype == "Customer")
			query = (
				query.where(DynamicLink.link_name == self.customer)
				if self.customer
				else query.where(fn.IfNull(DynamicLink.link_name, "") != "")
			)

		elif self.send_to == "All Supplier Contact":
			query = query.where(DynamicLink.link_doctype == "Supplier")
			query = (
				query.where(DynamicLink.link_name == self.supplier)
				if self.supplier
				else query.where(fn.IfNull(DynamicLink.link_name, "") != "")
			)

		elif self.send_to == "All Sales Partner Contact":
			query = query.where(DynamicLink.link_doctype == "Sales Partner")
			query = (
				query.where(DynamicLink.link_name == self.sales_partner)
				if self.sales_partner
				else query.where(fn.IfNull(DynamicLink.link_name, "") != "")
			)
		return query

	def get_contact_query_for_all_open_leads(self):
		Lead = frappe.qb.DocType("Lead")
		query = (
			frappe.qb.from_(Lead)
			.select(Lead.lead_name, Lead.mobile)
			.where((fn.IfNull(Lead.mobile_no, "") != "") & (Lead.docstatus != 2) & (Lead.status == "Open"))
		)
		return query

	def get_contact_query_for_all_active_employee(self):
		Employee = frappe.qb.DocType("Employee")
		query = (
			frappe.qb.from_(Employee)
			.select(Employee.employee_name, Employee.cell_number)
			.where(
				(Employee.status == "Active")
				& (Employee.docstatus != 2)
				& (fn.IfNull(Employee.cell_number, "") != "")
			)
		)

		if self.department:
			query = query.where(Employee.department == self.department)

		if self.branch:
			query = query.where(Employee.branch == self.branch)

		return query

	def get_contact_query_for_all_sales_person(self):
		SalesPerson = frappe.qb.DocType("Sales Person")
		Employee = frappe.qb.DocType("Employee")

		query = (
			frappe.qb.from_(SalesPerson)
			.left_join(Employee)
			.on(SalesPerson.employee == Employee.name)
			.select(SalesPerson.sales_person_name, Employee.cell_number)
			.where(fn.IfNull(Employee.cell_number, "") != "")
		)

		return query

	def get_receiver_nos(self):
		receiver_nos = []
		if self.receiver_list:
			for d in self.receiver_list.split("\n"):
				receiver_no = d
				if "-" in d:
					receiver_no = receiver_no.split("-")[1]
				if receiver_no.strip():
					receiver_nos.append(cstr(receiver_no).strip())
		else:
			msgprint(_("Receiver List is empty. Please create Receiver List"))

		return receiver_nos

	@frappe.whitelist()
	def send_sms(self):
		receiver_list = []
		if not self.message:
			msgprint(_("Please enter message before sending"))
		else:
			receiver_list = self.get_receiver_nos()
		if receiver_list:
			send_sms(receiver_list, cstr(self.message))
