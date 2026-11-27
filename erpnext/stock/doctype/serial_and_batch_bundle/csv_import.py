import frappe
import frappe.query_builder
from frappe import _
from frappe.utils import parse_json
from frappe.utils.csvutils import build_csv_response


@frappe.whitelist()
def download_blank_csv_template(content: str | list):
	csv_data = []
	if isinstance(content, str):
		content = parse_json(content)

	csv_data.append(content)
	csv_data.append([])
	csv_data.append([])

	filename = "serial_and_batch_bundle"
	build_csv_response(csv_data, filename)


@frappe.whitelist()
def read_serial_batch_csv(file_path: str):
	from frappe.utils.csvutils import read_csv_content

	serial_nos = []
	batch_nos = []

	if not file_path:
		return serial_nos, batch_nos

	from frappe.core.doctype.file.utils import find_file_by_url

	# look the file up through find_file_by_url, which returns it only when the caller may download it
	file = find_file_by_url(file_path)
	if not file:
		frappe.msgprint(
			_("File '{0}' not found").format(frappe.bold(file_path)),
			alert=True,
			indicator="red",
			raise_exception=FileNotFoundError,
		)

	file.check_permission("read")
	if file.file_type != "CSV":
		frappe.msgprint(
			_("{0} is not a CSV file.").format(frappe.bold(file.file_name)),
			alert=True,
			indicator="red",
			raise_exception=frappe.ValidationError,
		)

	csv_data = read_csv_content(file.get_content())
	return parse_csv_file_to_get_serial_batch(csv_data)


def parse_csv_file_to_get_serial_batch(reader):
	has_serial_no, has_batch_no = False, False
	serial_nos = []
	batch_nos = []

	for index, row in enumerate(reader):
		if index == 0:
			has_serial_no = row[0] == "Serial No"
			has_batch_no = row[0] == "Batch No"
			if not has_batch_no and len(row) > 1:
				has_batch_no = row[1] == "Batch No"

			continue

		if not row[0]:
			continue

		if has_serial_no or (has_serial_no and has_batch_no):
			_dict = {"serial_no": row[0].strip(), "qty": 1}

			if has_batch_no:
				_dict.update(
					{
						"batch_no": row[1].strip(),
						"qty": row[2],
					}
				)

				batch_nos.append(
					{
						"batch_no": row[1].strip(),
						"qty": row[2],
					}
				)

			serial_nos.append(_dict)
		elif has_batch_no:
			batch_nos.append(
				{
					"batch_no": row[0].strip(),
					"qty": row[1],
				}
			)

	return serial_nos, batch_nos
