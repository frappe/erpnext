import frappe, io, base64, urllib, os, json
from frappe.utils.file_manager import get_file_path

def pre_process(doc):

	file_path = doc.image
	file_name = os.path.basename(file_path)

	if file_path.startswith('http'):
		url = file_path
		file_path = os.path.join('/tmp', file_name)
		urllib.urlretrieve(url, file_path)
	else:
		file_path = os.path.abspath(get_file_path(file_path))

	try:
		with io.open(file_path, 'rb') as f:
			doc.image = json.dumps({
				'file_name': file_name,
				'base64': base64.b64encode(f.read())
			})
	except Exception as e:
		frappe.log_error(title='Hub Sync Error')

	cached_details = frappe.get_doc('Hub Tracked Item', doc.item_code)

	if cached_details:
		doc.hub_category = cached_details.hub_category
		doc.image_list = cached_details.image_list

	return doc

