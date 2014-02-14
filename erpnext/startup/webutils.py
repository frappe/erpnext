# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def update_website_context(context):
	if not context.get("favicon"):
		context["favicon"] = "app/images/favicon.ico"