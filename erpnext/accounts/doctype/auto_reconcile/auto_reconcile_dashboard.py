from frappe import _


def get_data():
	return {
		"fieldname": "auto_reconcile",
		"transactions": [
			{
				"label": _("Reconciliation Logs"),
				"items": [
					"Auto Reconcile Log",
				],
			},
		],
	}
