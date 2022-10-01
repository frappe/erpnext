import json
import os

from frappe.desk.page.setup_wizard.setup_wizard import setup_complete


def complete():
	with open(os.path.join(os.path.dirname(__file__), "data", "test_mfg.json"), "r") as f:
		data = json.loads(f.read())

	setup_complete(data)
