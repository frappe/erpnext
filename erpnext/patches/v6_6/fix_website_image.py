from __future__ import print_function, unicode_literals
import frappe
from frappe.utils import encode

def execute():
	"""Fix the File records created via item.py even if the website_image file didn't exist"""
	for item in frappe.db.sql_list("""select name from `tabItem`
		where website_image is not null and website_image != ''
			and website_image like '/files/%'
			and exists (
				select name from `tabFile`
					where attached_to_doctype='Item'
					and attached_to_name=`tabItem`.name
					and file_url=`tabItem`.website_image
					and (file_name is null or file_name = '')
				)"""):

		item = frappe.get_doc("Item", item)
		file = frappe.get_doc("File", {
			"attached_to_doctype": "Item",
			"attached_to_name": item.name,
			"file_url": item.website_image
		})

		try:
			file.validate_file()
		except IOError:
			print(encode(item.website_image), "does not exist")
			file.delete()
			item.db_set("website_image", None, update_modified=False)


