import click


def execute():
	click.secho(
		"DATEV reports are moved to a separate app and will be removed from ERPNext in version-14.\n"
		"Please install the app to continue using them: https://github.com/alyf-de/erpnext_datev",
		fg="yellow",
	)
