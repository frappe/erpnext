import json
import re

import frappe
import frappe.sessions
from frappe import _
from frappe.utils.jinja_globals import is_rtl

no_cache = 1

SCRIPT_TAG_PATTERN = re.compile(r"\<script[^<]*\</script\>", re.IGNORECASE)
CLOSING_SCRIPT_TAG_PATTERN = re.compile(r"</script\>", re.IGNORECASE)


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()

	context = frappe._dict()
	context.boot = get_boot()
	context.csrf_token = csrf_token
	context.build_version = frappe.utils.get_build_version()
	context.app_name = (
		frappe.get_website_settings("app_name") or frappe.get_system_settings("app_name") or "ERPNext"
	)

	context.layout_direction = "rtl" if is_rtl() else "ltr"
	context.lang = frappe.local.lang

	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))
	return {
		"boot": json.loads(get_boot()),
		"layout_direction": "rtl" if is_rtl() else "ltr",
	}


def get_boot():
	try:
		boot = frappe.sessions.get()
	except Exception as e:
		raise frappe.SessionBootFailed from e

	boot_json = frappe.as_json(boot, indent=None, separators=(",", ":"))
	boot_json = SCRIPT_TAG_PATTERN.sub("", boot_json)

	boot_json = CLOSING_SCRIPT_TAG_PATTERN.sub("", boot_json)
	boot_json = json.dumps(boot_json)

	return boot_json
