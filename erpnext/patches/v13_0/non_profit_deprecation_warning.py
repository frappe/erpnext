import click


def execute():
	click.secho(
		"Non Profit Domain is moved to a separate app and will be removed from ZirakERP in version-14.\n"
		"When upgrading to ZirakERP version-14, please install the app to continue using the Non Profit domain: https://github.com/frappe/non_profit",
		fg="yellow",
	)
