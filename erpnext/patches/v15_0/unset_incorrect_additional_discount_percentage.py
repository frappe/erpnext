import frappe
from frappe import scrub
from frappe.model.meta import get_field_precision
from frappe.utils import flt
from semantic_version import Version

from erpnext.accounts.report.calculated_discount_mismatch.calculated_discount_mismatch import (
	AFFECTED_DOCTYPES,
	LAST_MODIFIED_DATE_THRESHOLD,
)


def execute():
	# run this patch only if erpnext version before update is v15.64.0 or higher
	if not should_run_patch():
		return

	for doctype in AFFECTED_DOCTYPES:
		meta = frappe.get_meta(doctype)
		filters = {
			"modified": [">", LAST_MODIFIED_DATE_THRESHOLD],
			"additional_discount_percentage": [">", 0],
			"discount_amount": ["!=", 0],
		}

		# can't reverse calculate grand_total if shipping rule is set
		if meta.has_field("shipping_rule"):
			filters["shipping_rule"] = ["is", "not set"]

		documents = frappe.get_all(
			doctype,
			fields=[
				"name",
				"additional_discount_percentage",
				"discount_amount",
				"apply_discount_on",
				"grand_total",
				"net_total",
			],
			filters=filters,
		)

		if not documents:
			continue

		precision = get_field_precision(frappe.get_meta(doctype).get_field("additional_discount_percentage"))
		mismatched_documents = []

		for doc in documents:
			# we need grand_total before applying discount
			doc.grand_total += doc.discount_amount
			discount_applied_on = scrub(doc.apply_discount_on)
			calculated_discount_amount = flt(
				doc.additional_discount_percentage * doc.get(discount_applied_on) / 100,
				precision,
			)

			# if difference is more than 0.02 (based on precision), unset the additional discount percentage
			if abs(calculated_discount_amount - doc.discount_amount) > 2 / (10**precision):
				mismatched_documents.append(doc.name)

		if mismatched_documents:
			# changing the discount percentage has no accounting effect
			# so we can safely set it to 0 in the database
			frappe.db.set_value(
				doctype,
				{"name": ["in", mismatched_documents]},
				"additional_discount_percentage",
				0,
				update_modified=False,
			)


def get_semantic_version(version):
	try:
		return Version(version)
	except Exception:
		pass


def should_run_patch():
	installed_app = frappe.db.get_value(
		"Installed Application",
		{"app_name": "erpnext"},
		["app_version", "git_branch"],
	)

	if not installed_app:
		return True

	version, git_branch = installed_app
	semantic_version = get_semantic_version(version)
	if not semantic_version:
		return True

	return not (
		semantic_version.major < 15
		or (git_branch == "version-15" and semantic_version.major == 15 and semantic_version.minor < 64)
	)
