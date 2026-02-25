import frappe

from perceptrons.setup.install import create_default_success_action


def execute():
	frappe.reload_doc("core", "doctype", "success_action")
	create_default_success_action()
