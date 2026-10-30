# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, session
from frappe.utils import escape_html, getdate, now_datetime

from erpnext.utilities.transaction_base import TransactionBase


class WarrantyClaim(TransactionBase):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address_display: DF.TextEditor | None
		amc_expiry_date: DF.Date | None
		amended_from: DF.Link | None
		company: DF.Link
		complaint: DF.TextEditor
		complaint_date: DF.Date
		complaint_raised_by: DF.Data | None
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.Data | None
		contact_person: DF.Link | None
		customer: DF.Link
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		description: DF.SmallText | None
		from_company: DF.Data | None
		item_code: DF.Link | None
		item_name: DF.Data | None
		naming_series: DF.Literal["SER-WRN-.YYYY.-"]
		resolution_date: DF.Datetime | None
		resolution_details: DF.Text | None
		resolved_by: DF.Link | None
		serial_no: DF.Link | None
		service_address: DF.SmallText | None
		status: DF.Literal["", "Open", "Closed", "Work In Progress", "Cancelled"]
		territory: DF.Link | None
		warranty_amc_status: DF.Literal["", "Under Warranty", "Out of Warranty", "Under AMC", "Out of AMC"]
		warranty_expiry_date: DF.Date | None
	# end: auto-generated types

	def validate(self):
		self.validate_serial_no()
		self.warn_if_serial_no_not_delivered_to_customer()
		if self.status == "Cancelled" and self.has_value_changed("status"):
			self.validate_no_active_visits()
		if session["user"] != "Guest" and not self.customer:
			frappe.throw(_("Customer is required"))

		self.set_resolution()
		self.set_warranty_amc_status()

	def validate_serial_no(self):
		if not self.serial_no or not self.item_code:
			return
		serial = frappe.db.get_value("Serial No", self.serial_no, ["serial_no", "item_code"], as_dict=True)
		if serial and serial.item_code != self.item_code:
			frappe.throw(
				_("Serial No {0} does not belong to Item {1}").format(
					escape_html(serial.serial_no), escape_html(self.item_code)
				)
			)

	def set_resolution(self):
		previous_status = frappe.db.get_value("Warranty Claim", self.name, "status")
		if self.status == "Closed" and not self.resolution_date and previous_status != "Closed":
			self.resolution_date = now_datetime()
		elif self.status != "Closed" and previous_status == "Closed":
			self.resolution_date = None
			self.resolved_by = None

	def set_warranty_amc_status(self):
		"""Warranty / AMC status on the complaint date, ranked as on Serial No."""
		if not (self.warranty_expiry_date or self.amc_expiry_date):
			return

		complaint_date = getdate(self.complaint_date)
		warranty_expiry = self.warranty_expiry_date and getdate(self.warranty_expiry_date)
		amc_expiry = self.amc_expiry_date and getdate(self.amc_expiry_date)

		if warranty_expiry and warranty_expiry >= complaint_date:
			self.warranty_amc_status = "Under Warranty"
		elif amc_expiry:
			self.warranty_amc_status = "Under AMC" if amc_expiry >= complaint_date else "Out of AMC"
		else:
			self.warranty_amc_status = "Out of Warranty"

	def warn_if_serial_no_not_delivered_to_customer(self) -> None:
		"""Warn only: a serial can change hands without a delivery, so the claim is still allowed."""
		if not (self.serial_no and self.customer):
			return
		if not (self.has_value_changed("serial_no") or self.has_value_changed("customer")):
			return

		if message := self.get_serial_no_ownership_warning():
			frappe.msgprint(message, title=_("Check Serial No"), indicator="orange")

	def get_serial_no_ownership_warning(self) -> str | None:
		serial = frappe.db.get_value("Serial No", self.serial_no, ["customer", "warehouse"], as_dict=True)
		if not serial:
			return None

		serial_no = frappe.bold(escape_html(self.serial_no))
		if serial.customer and serial.customer != self.customer:
			return _("Serial No {0} was delivered to Customer {1}, not to {2}.").format(
				serial_no, frappe.bold(escape_html(serial.customer)), frappe.bold(escape_html(self.customer))
			)
		if not serial.customer and serial.warehouse:
			return _(
				"Serial No {0} is still in stock in Warehouse {1} and was not delivered to a customer."
			).format(serial_no, frappe.bold(escape_html(serial.warehouse)))
		return None

	def validate_no_active_visits(self):
		lst = frappe.db.sql(
			"""select t1.name
			from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
			where t2.parent = t1.name and t2.prevdoc_docname = %s and	t1.docstatus!=2""",
			(self.name),
		)
		if lst:
			lst1 = ",".join(x[0] for x in lst)
			frappe.throw(_("Cancel Material Visit {0} before cancelling this Warranty Claim").format(lst1))

	def on_update(self):
		pass


@frappe.whitelist()
def make_maintenance_visit(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc, map_child_doc

	def _update_links(source_doc, target_doc, source_parent):
		target_doc.prevdoc_doctype = source_parent.doctype
		target_doc.prevdoc_docname = source_parent.name

	visit = frappe.db.sql(
		"""select t1.name
		from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
		where t2.parent=t1.name and t2.prevdoc_docname=%s
		and t1.docstatus=1 and t1.completion_status='Fully Completed'""",
		source_name,
	)

	if not visit:
		target_doc = get_mapped_doc(
			"Warranty Claim",
			source_name,
			{"Warranty Claim": {"doctype": "Maintenance Visit", "field_map": {}}},
			target_doc,
		)

		source_doc = frappe.get_doc("Warranty Claim", source_name)
		if source_doc.get("item_code"):
			table_map = {"doctype": "Maintenance Visit Purpose", "postprocess": _update_links}
			map_child_doc(source_doc, target_doc, table_map, source_doc)

		return target_doc
