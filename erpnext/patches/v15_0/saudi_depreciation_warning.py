import click


def execute():

	click.secho(
		"Saudi Arabia Region is moved to a separate app and will be removed from ERPNext in version-15.\n"
		"When upgrading to ERPNext version-15, please install the app to continue using the Education domain: https://github.com/8848digital/KSA",
		fg="yellow",
	)