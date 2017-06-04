# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe


def get_context(context):
	topic = frappe.get_doc('Topic', frappe.form_dict.topic)
	context.no_cache = 1
	context.show_sidebar = True
	context.doc = topic
	attachments = frappe.db.sql("""select file_url, file_name from tabFile as file
								where file.attached_to_name=%s """,(topic.name), as_dict = True)

	context.attached_files = attachments
