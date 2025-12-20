import click


def execute():
	click.secho(
		"Healthcare Module is moved to a separate app and will be removed from ERPNext in version-14.\n"
		"Please install the app to continue using the module: https://github.com/frappe/healthcare",
		fg="yellow",
	)
