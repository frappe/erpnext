# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.notifications import clear_notifications
from frappe.model.document import Document
from frappe.utils import cint

IGNORED_DOCTYPES = {
	"Account",
	"Cost Center",
	"Warehouse",
	"Budget",
	"Party Account",
	"Employee",
	"Sales Taxes and Charges Template",
	"Purchase Taxes and Charges Template",
	"POS Profile",
	"BOM",
	"Company",
	"Bank Account",
	"Item Tax Template",
	"Mode of Payment",
	"Item Default",
	"Customer",
	"Supplier",
}


class TransactionDeletionRecord(Document):
	def validate(self):
		frappe.only_for("System Manager")

		if {row.doctype_name for row in self.doctypes_to_be_ignored}.difference(IGNORED_DOCTYPES):
			frappe.throw(
				_(
					"DocTypes should not be added manually to the 'Excluded DocTypes' table. You are only allowed to remove entries from it."
				),
				title=_("Not Allowed"),
			)

	def before_submit(self):
		self.populate_doctypes_to_be_ignored_table()
		delete_bins(self.company)
		delete_lead_addresses(self.company)
		reset_company_values(self.company)
		clear_notifications()
		self.delete_company_transactions()

	def populate_doctypes_to_be_ignored_table(self):
		if self.doctypes_to_be_ignored:
			return

		self.extend(
			"doctypes_to_be_ignored", [{"doctype_name": doctype} for doctype in IGNORED_DOCTYPES]
		)

	def delete_company_transactions(self):
		table_doctypes = frappe.get_all("DocType", filters={"istable": 1}, pluck="name")
		exclude_doctypes = {row.doctype_name for row in self.doctypes_to_be_ignored} | get_singles()

		for doctype, fieldname in get_doctypes_with_company_field(exclude_doctypes):
			if doctype == self.doctype:
				continue

			no_of_docs = frappe.db.count(doctype, {fieldname: self.company})
			if no_of_docs <= 0:
				continue

			if doctype not in table_doctypes:
				self.append("doctypes", {"doctype_name": doctype, "no_of_docs": no_of_docs})

			reference_docs = frappe.get_all(doctype, filters={fieldname: self.company}, pluck="name")

			frappe.db.delete("Version", {"ref_doctype": doctype, "docname": ("in", reference_docs)})
			frappe.db.delete(
				"Communication", {"reference_doctype": doctype, "reference_name": ("in", reference_docs)}
			)
			for table in frappe.get_all(
				"DocField", filters={"fieldtype": "Table", "parent": doctype}, pluck="options"
			):
				frappe.db.delete(table, {"parent": ("in", reference_docs)})

			frappe.db.delete(doctype, {fieldname: self.company})

			if naming_series := frappe.db.get_value("DocType", doctype, "autoname"):
				if "#" in naming_series:
					update_naming_series(naming_series, doctype)


def get_singles() -> set[str]:
	return set(frappe.get_all("DocType", filters={"issingle": 1}, pluck="name"))


def update_naming_series(naming_series, doctype_name):
	from pypika.functions import Max

	if "." in naming_series:
		prefix = naming_series.rsplit(".", 1)[0]
	elif "{" in naming_series:
		prefix = naming_series.rsplit("{", 1)[0]
	else:
		prefix = naming_series

	table = frappe.qb.DocType(doctype_name)
	last = frappe.qb.from_(table).select(Max(table.name)).where(table.name.like(f"{prefix}%")).run()

	last = cint(last[0][0].replace(prefix, "")) if last and last[0][0] else 0
	series = frappe.qb.DocType("Series")
	frappe.qb.update(series).set(series.current, last).where(series.name == prefix).run()


@frappe.whitelist()
def get_doctypes_to_be_ignored():
	return list(IGNORED_DOCTYPES)


def get_doctypes_with_company_field(exclude_doctypes) -> tuple[tuple[str, str]]:
	return frappe.get_all(
		"DocField",
		filters={
			"fieldtype": "Link",
			"options": "Company",
			"parent": ("not in", exclude_doctypes),
		},
		fields=["parent", "fieldname"],
		as_list=True,
	)


def reset_company_values(compay_name: str) -> None:
	company_obj = frappe.get_doc("Company", compay_name)
	company_obj.total_monthly_sales = 0
	company_obj.sales_monthly_history = None
	company_obj.save()


def delete_bins(compay_name: str) -> None:
	company_warehouses = frappe.get_all("Warehouse", filters={"company": compay_name}, pluck="name")
	frappe.db.delete("Bin", {"warehouse": ("in", company_warehouses)})


def delete_lead_addresses(company_name: str) -> None:
	"""Delete addresses to which leads are linked"""
	leads = frappe.get_all("Lead", filters={"company": company_name}, pluck="name")
	if not leads:
		return

	if addresses := frappe.get_all(
		"Dynamic Link",
		filters={"link_name": ("in", leads), "link_doctype": "Lead", "parenttype": "Address"},
		pluck="parent",
	):
		dl1, dl2 = frappe.qb.DocType("Dynamic Link"), frappe.qb.DocType("Dynamic Link")
		address = frappe.qb.DocType("Address")
		frappe.qb.from_(address).delete().where(address.name.isin(addresses)).where(
			address.name.notin(
				frappe.qb.from_(dl1)
				.inner_join(dl2)
				.on((dl1.parent == dl2.parent) & (dl1.link_doctype != dl2.link_doctype))
				.select(dl1.parent)
			)
		).run()
		frappe.qb.from_(dl1).delete().where(dl1.link_doctype == "Lead").where(
			dl1.parenttype == "Address"
		).where(dl1.link_name.isin(leads)).run()

	customer = frappe.qb.DocType("Customer")
	frappe.qb.update(customer).set(customer.lead_name, None).where(
		customer.lead_name.isin(leads)
	).run()
