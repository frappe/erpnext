# Copyright (c) 2019


import frappe


def execute():
	frappe.delete_doc("Page", "medical_record")
