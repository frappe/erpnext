# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class IntegrationService(Document):
	def validate(self):
		self.validate_module()

	def validate_module(self):
		try:
			self.config = frappe.get_module("erpnext.integration_controller.controllers.{service}.config"
				.format(service=self.service.strip().lower().replace(' ','_')))
		except ImportError:
			frappe.throw(_("Module {service} not found".format(service=self.service)))

	def on_update(self):
		if self.enabled:
			self.enable_service()
			self.install_fixtures()

	def install_fixtures(self):
		pass

	def enable_service(self):
		service = frappe.get_module("erpnext.integration_controller.controllers.{service}.{service}"
			.format(service=self.service.strip().lower().replace(' ','_')))
		service.enable_service(self)

	def set_service_config(self):
		self.validate_module()
		
		service_config = self.config.get_config()
		
		self.set_authentication_details(service_config)
		self.set_service_events(service_config)

	def set_authentication_details(self, service_config):
		self.set("authentication_details", [])
		self.extend("authentication_details", service_config["authentication_details"])
	
	def set_service_events(self, service_config):
		self.set("service_events", [])

		for event_dict in service_config["service_events"]:
			self.append("service_events", {
				"event": event_dict["event"],
				"enabled": event_dict["enabled"]
			})

@frappe.whitelist()
def get_integration_services():
	services = [""]
	for app in frappe.get_installed_apps():
		services.extend(frappe.get_hooks("integration_services", app_name = app))
	
	return services
		