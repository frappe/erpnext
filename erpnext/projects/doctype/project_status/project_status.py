# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.safe_exec import safe_exec
import json


class ProjectStatus(Document):
	def on_change(self):
		clear_project_status_cache()

	def after_rename(self, old_name, new_name, merge):
		clear_project_status_cache()


def clear_project_status_cache():
	frappe.cache().delete_value('project_status_names')


def get_project_status_names():
	def generator():
		return [d.name for d in frappe.get_all('Project Status', filters={'disabled': 0}, order_by="sorting_index, name")]

	return frappe.cache().get_value('project_status_names', generator)


def get_project_status_docs():
	names = get_project_status_names()
	docs = [frappe.get_cached_doc("Project Status", name) for name in names]
	return docs


def get_auto_project_status_docs():
	project_statuses = get_project_status_docs()
	manual_project_status_docs = [d for d in project_statuses if not d.manual_status]
	return manual_project_status_docs


def get_auto_project_status_names():
	docs = get_auto_project_status_docs()
	return [d.name for d in docs]


def get_manual_project_status_docs():
	project_statuses = get_project_status_docs()
	manual_project_status_docs = [d for d in project_statuses if d.manual_status]
	return manual_project_status_docs


def get_manaul_project_status_names():
	docs = get_manual_project_status_docs()
	return [d.name for d in docs]


def get_valid_manual_project_status_docs(project):
	valid_docs = []

	all_docs = get_manual_project_status_docs()
	for project_status_doc in all_docs:
		if not project_status_doc.user_can_set:
			continue

		condition_met = evaluate_project_status_condition(project_status_doc, project)
		if condition_met:
			valid_docs.append(project_status_doc)

	return valid_docs


def get_valid_manual_project_status_names(project):
	docs = get_valid_manual_project_status_docs(project)
	return [d.name for d in docs]


def is_manual_project_status(project_status):
	if project_status and project_status in get_manaul_project_status_names():
		return True
	else:
		return False


def get_auto_project_status(project):
	auto_project_status_docs = get_auto_project_status_docs()

	# is current status a valid manually set status do not change
	if is_manual_project_status(project.project_status):
		project_status_doc = frappe.get_cached_doc("Project Status", project.project_status)
		condition_met = evaluate_project_status_condition(project_status_doc, project)
		if condition_met:
			return project_status_doc

	# evaluate all project status coniditions
	for project_status_doc in auto_project_status_docs:
		condition_met = evaluate_project_status_condition(project_status_doc, project)
		if condition_met:
			return project_status_doc


def set_manual_project_status(project, project_status):
	project_status_names = get_project_status_names()

	if project_status not in project_status_names:
		frappe.throw(_("{0} is not a valid Project Status").format(frappe.bold(project_status)))

	project_status_doc = frappe.get_cached_doc("Project Status", project_status)

	if not project_status_doc.manual_status:
		frappe.throw(_("Not allowed to manually set Project Status as {0}").format(frappe.bold(project_status)))

	# run validation script first (for specific error messages)
	execute_project_status_validation(project_status_doc, project, 'on_set_validation')

	# then evaluate condition
	if not evaluate_project_status_condition(project_status_doc, project):
		frappe.throw(_("Project Status cannot be set to {0} because status condition was not met")
			.format(frappe.bold(project_status)))

	project.project_status = project_status


def validate_project_status_for_transaction(project, transaction):
	if project.project_status and transaction and project.project_status in get_project_status_names():
		project_status_doc = frappe.get_cached_doc("Project Status", project.project_status)
		execute_project_status_validation(project_status_doc, project, "transaction_validation",
			context={'transaction': transaction})


def evaluate_project_status_condition(project_status_doc, project):
	if not project_status_doc.condition:
		return True

	condition_met = frappe.safe_eval(project_status_doc.condition, None, {"doc": project})
	if condition_met:
		return True

	return False


def execute_project_status_validation(project_status_doc, project, validation_field, context=None):
	if not project_status_doc.get(validation_field):
		return

	context = frappe._dict(context or {})
	context.update({"doc": project})

	safe_exec(project_status_doc.get(validation_field), None, context)
