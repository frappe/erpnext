import click
import frappe


def execute():
	to_delete = {
		"DocType": [
			"C-Form",
			"C-Form Invoice Detail",
			"GST Account",
			"E Invoice Request Log",
			"E Invoice Settings",
			"E Invoice User",
			"GST HSN Code",
			"GST Settings",
			"GSTR 3B Report",
		],
		"Print Format": [
			"GST E-Invoice",
			"GST Purchase Invoice",
			"GST Tax Invoice",
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
		frappe.delete_doc(doctype, names, ignore_missing=True, force=True)

	click.secho(
		"Regional India is moved to a separate app and is removed from ERPNext.\n"
		"Please install the app to continue using the module: https://github.com/resilient-tech/india-compliance",
		fg="yellow",
	)
