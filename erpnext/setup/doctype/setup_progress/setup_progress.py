# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document

class SetupProgress(Document):
	pass

def get_setup_progress():
	if not getattr(frappe.local, "setup_progress", None):
		frappe.local.setup_progress = frappe.get_doc("Setup Progress", "Setup Progress")

	return frappe.local.setup_progress

def get_action_completed_state(action_name):
	return [d.is_completed for d in get_setup_progress().actions
		if d.action_name == action_name][0]

def update_action_completed_state(action_name):
	action_table_doc = [d for d in get_setup_progress().actions
		if d.action_name == action_name][0]
	update_action(action_table_doc)

def update_action(action_table_doc):
	if not action_table_doc.is_completed and frappe.db.count(action_table_doc.action_doctype) >= action_table_doc.min_doc_count:
		action_table_doc.is_completed = 1
		action_table_doc.save()

def update_domain_actions(domain):
	for d in get_setup_progress().actions:
		domains = json.loads(d.domains)
		if domains == [] or domain in domains:
			update_action(d)

def get_domain_actions_state(domain):
	state = {}
	for d in get_setup_progress().actions:
		domains = json.loads(d.domains)
		if domains == [] or domain in domains:
			state[d.action_name] = d.is_completed
	return state

@frappe.whitelist()
def set_action_completed_state(action_name):
	action_table_doc = [d for d in get_setup_progress().actions
		if d.action_name == action_name][0]
	action_table_doc.is_completed = 1
	action_table_doc.save()
