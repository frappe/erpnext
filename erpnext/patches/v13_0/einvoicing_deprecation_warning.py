import click


def execute():
	click.secho(
		"Indian E-Invoicing integration is moved to a separate app and will be removed from ERPNext in version-14.\n"
		"Please install the app to continue using the integration: https://github.com/frappe/erpnext_gst_compliance",
		fg="yellow",
	)
