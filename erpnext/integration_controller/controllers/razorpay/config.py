# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe

def get_config():
	return {
		"has_custom_fields": 0,
		"authentication_details": [
			{
				"parameter": "API Key"
			},
			{
				"parameter": "API Secret"
			},
		],
		"service_events":[
			{
				"event": "Payment Initialization",
				"enabled": 1,
				"handler": ""
			},
			{
				"event": "Payment Completion",
				"enabled": 0,
				"handler": ""
			},
		]
	}