import click
import frappe


def execute():
	if "india_compliance" in frappe.get_installed_apps():
		return

	delete_docs()
	unlink_custom_fields()

	if not frappe.db.exists("Company", {"country": "India"}):
		return

	click.secho(
		"India-specific regional features have been moved to a separate app."
		" Please install India Compliance to continue using these features:"
		" https://github.com/resilient-tech/india-compliance",
		fg="yellow",
	)


def delete_docs():
	to_delete = {
		"DocType": [
			"C-Form",
			"C-Form Invoice Detail",
			"GST Account",
			"E Invoice Request Log",
			"E Invoice Settings",
			"E Invoice User",
			"GST HSN Code",
			"HSN Tax Rate",
			"GST Settings",
			"GSTR 3B Report",
		],
		"Print Format": [
			"GST E-Invoice",
			"GST Purchase Invoice",
			"GST Tax Invoice",
			"GST POS Invoice",
		],
		"Report": [
			"E-Invoice Summary",
			"Eway Bill",
			"GST Itemised Purchase Register",
			"GST Itemised Sales Register",
			"GST Purchase Register",
			"GST Sales Register",
			"GSTR-1",
			"GSTR-2",
			"HSN-wise-summary of outward supplies",
		],
	}

	for doctype, names in to_delete.items():
		frappe.delete_doc(
			doctype,
			names,
			force=True,
			ignore_permissions=True,
			ignore_missing=True,
		)


def unlink_custom_fields():
	frappe.db.set_value(
		"Custom Field",
		{"dt": "Item", "fieldname": "gst_hsn_code"},
		{"fieldtype": "Data", "options": ""},
	)
