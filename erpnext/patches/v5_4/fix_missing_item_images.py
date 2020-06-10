from __future__ import print_function, unicode_literals
import frappe
import os
from frappe.utils import get_files_path
from frappe.core.doctype.file.file import get_content_hash

def execute():
	files_path = get_files_path()

	# get files that don't have attached_to_name but exist
	unlinked_files = get_unlinked_files(files_path)
	if not unlinked_files:
		return

	fixed_files = fix_files_for_item(files_path, unlinked_files)

	# fix remaining files
	for key, file_data in unlinked_files.items():
		if key not in fixed_files:
			rename_and_set_content_hash(files_path, unlinked_files, key)
			frappe.db.commit()

def fix_files_for_item(files_path, unlinked_files):
	fixed_files = []

	# make a list of files/something and /files/something to check in child table's image column
	file_urls = [key for key in unlinked_files.keys()] + ["/" + key for key in unlinked_files.keys()]
	file_item_code = get_file_item_code(file_urls)

	for (file_url, item_code), children in file_item_code.items():
		new_file_url = "/files/{0}".format(unlinked_files[file_url]["file_name"])

		for row in children:
			# print file_url, new_file_url, item_code, row.doctype, row.name

			# replace image in these rows with the new file url
			frappe.db.set_value(row.doctype, row.name, "image", new_file_url, update_modified=False)

		# set it as attachment of this item code
		file_data = frappe.get_doc("File", unlinked_files[file_url]["file"])
		file_data.attached_to_doctype = "Item"
		file_data.attached_to_name = item_code
		file_data.flags.ignore_folder_validate = True

		try:
			file_data.save()
		except IOError:
			print("File {0} does not exist".format(new_file_url))

			# marking fix to prevent further errors
			fixed_files.append(file_url)

			continue

		# set it as image in Item
		if not frappe.db.get_value("Item", item_code, "image"):
			frappe.db.set_value("Item", item_code, "image", new_file_url, update_modified=False)

		rename_and_set_content_hash(files_path, unlinked_files, file_url)

		fixed_files.append(file_url)

		# commit
		frappe.db.commit()

	return fixed_files

def rename_and_set_content_hash(files_path, unlinked_files, file_url):
	# rename this file
	old_filename = os.path.join(files_path, unlinked_files[file_url]["file"])
	new_filename = os.path.join(files_path, unlinked_files[file_url]["file_name"])

	if not os.path.exists(new_filename):
		os.rename(old_filename, new_filename)

	# set content hash if missing
	file_data_name = unlinked_files[file_url]["file"]
	if not frappe.db.get_value("File", file_data_name, "content_hash"):
		with open(new_filename, "r") as f:
			content_hash = get_content_hash(f.read())
			frappe.db.set_value("File", file_data_name, "content_hash", content_hash)

def get_unlinked_files(files_path):
	# find files that have the same name as a File doc
	# and the file_name mentioned in that File doc doesn't exist
	# and it isn't already attached to a doc
	unlinked_files = {}
	files = os.listdir(files_path)
	for file in files:
		if not frappe.db.exists("File", {"file_name": file}):
			file_data = frappe.db.get_value("File", {"name": file},
				["file_name", "attached_to_doctype", "attached_to_name"], as_dict=True)

			if (file_data
				and file_data.file_name
				and file_data.file_name not in files
				and not file_data.attached_to_doctype
				and not file_data.attached_to_name):

				file_data["file"] = file
				unlinked_files["files/{0}".format(file)] = file_data

	return unlinked_files

def get_file_item_code(file_urls):
	# get a map of file_url, item_code and list of documents where file_url will need to be changed in image field
	file_item_code = {}

	doctypes = frappe.db.sql_list("""select name from `tabDocType` dt
		where istable=1
			and exists (select name from `tabDocField` df where df.parent=dt.name and df.fieldname='item_code')
			and exists (select name from `tabDocField` df where df.parent=dt.name and df.fieldname='image')""")

	for doctype in doctypes:
		result = frappe.db.sql("""select name, image, item_code, '{0}' as doctype from `tab{0}`
				where image in ({1})""".format(doctype, ", ".join(["%s"]*len(file_urls))),
				file_urls, as_dict=True)

		for r in result:
			key = (r.image, r.item_code)
			if key not in file_item_code:
				file_item_code[key] = []

			file_item_code[key].append(r)

	return file_item_code
