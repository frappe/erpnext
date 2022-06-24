import click


def execute():

	click.secho(
		"Regional India is moved to a separate app and will be removed from ERPNext in version-14.\n"
		"Please install the app to continue using the module after upgrading to version-14: https://github.com/resilient-tech/india-compliance",
		fg="yellow",
	)
