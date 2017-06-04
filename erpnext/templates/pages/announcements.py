# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def get_context(context):
	announcement = frappe.get_doc('Announcement', frappe.form_dict.announcement)
	context.no_cache = 1
	context.show_sidebar = True
	announcement.has_permission('read')
	context.doc = announcement
	attachments = frappe.db.sql("""select file_url, file_name from tabFile as file
								where file.attached_to_name=%s """,(announcement.name), as_dict = True)

	context.attached_files = attachments


