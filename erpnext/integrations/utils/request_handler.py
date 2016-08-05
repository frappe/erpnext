# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json, urlparse
from frappe.utils import get_request_session

def get_request(url, auth=None, data=None):
	if not auth:
		auth = ''
	if not data:
		data = {}

	try:
		s = get_request_session()
		res = s.get(url, data={}, auth=auth)
		res.raise_for_status()
		return res.json()

	except Exception, exc:
		raise exc

def put_request(url, auth=None, data=None):
	pass

def post_request(url, auth=None, data=None):
	if not auth:
		auth = ''
	if not data:
		data = {}
	try:
		s = get_request_session()
		res = s.post(url, data=data, auth=auth)
		res.raise_for_status()
		if res.headers.get("content-type") == "text/plain":
			return urlparse.parse_qs(res.text)
		
		return res.json()
	except Exception, exc:
		raise exc

def make_request(data, integration_type, service_name):
	if not isinstance(data, basestring):
		data = json.dumps(data)
	
	integration_request = frappe.get_doc({
		"doctype": "Integration Request",
		"integration_type": integration_type,
		"integration_request_service": service_name,
		"data": data
	}).insert(ignore_permissions=True)
	
	return integration_request