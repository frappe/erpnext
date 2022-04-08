import io
import os
from base64 import b64encode

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils.data import add_to_date, get_time, getdate
from pyqrcode import create as qr_create

from erpnext import get_region


def create_qr_code(doc, method=None):
	region = get_region(doc.company)
	if region not in ["Saudi Arabia"]:
		return

	# if QR Code field not present, create it. Invoices without QR are invalid as per law.
	if not hasattr(doc, "ksa_einv_qr"):
		create_custom_fields(
			{
				doc.doctype: [
					dict(
						fieldname="ksa_einv_qr",
						label="KSA E-Invoicing QR",
						fieldtype="Attach Image",
						read_only=1,
						no_copy=1,
						hidden=1,
					)
				]
			}
		)

	# Don't create QR Code if it already exists
	qr_code = doc.get("ksa_einv_qr")
	if qr_code and frappe.db.exists({"doctype": "File", "file_url": qr_code}):
		return

	meta = frappe.get_meta(doc.doctype)

	if "ksa_einv_qr" in [d.fieldname for d in meta.get_image_fields()]:
		"""TLV conversion for
		1. Seller's Name
		2. VAT Number
		3. Time Stamp
		4. Invoice Amount
		5. VAT Amount
		"""
		tlv_array = []
		# Sellers Name

		seller_name = frappe.db.get_value("Company", doc.company, "company_name_in_arabic")

		if not seller_name:
			frappe.throw(_("Arabic name missing for {} in the company document").format(doc.company))

		tag = bytes([1]).hex()
		length = bytes([len(seller_name.encode("utf-8"))]).hex()
		value = seller_name.encode("utf-8").hex()
		tlv_array.append("".join([tag, length, value]))

		# VAT Number
		tax_id = frappe.db.get_value("Company", doc.company, "tax_id")
		if not tax_id:
			frappe.throw(_("Tax ID missing for {} in the company document").format(doc.company))

		tag = bytes([2]).hex()
		length = bytes([len(tax_id)]).hex()
		value = tax_id.encode("utf-8").hex()
		tlv_array.append("".join([tag, length, value]))

		# Time Stamp
		posting_date = getdate(doc.posting_date)
		time = get_time(doc.posting_time)
		seconds = time.hour * 60 * 60 + time.minute * 60 + time.second
		time_stamp = add_to_date(posting_date, seconds=seconds)
		time_stamp = time_stamp.strftime("%Y-%m-%dT%H:%M:%SZ")

		tag = bytes([3]).hex()
		length = bytes([len(time_stamp)]).hex()
		value = time_stamp.encode("utf-8").hex()
		tlv_array.append("".join([tag, length, value]))

		# Invoice Amount
		invoice_amount = str(doc.grand_total)
		tag = bytes([4]).hex()
		length = bytes([len(invoice_amount)]).hex()
		value = invoice_amount.encode("utf-8").hex()
		tlv_array.append("".join([tag, length, value]))

		# VAT Amount
		vat_amount = str(get_vat_amount(doc))

		tag = bytes([5]).hex()
		length = bytes([len(vat_amount)]).hex()
		value = vat_amount.encode("utf-8").hex()
		tlv_array.append("".join([tag, length, value]))

		# Joining bytes into one
		tlv_buff = "".join(tlv_array)

		# base64 conversion for QR Code
		base64_string = b64encode(bytes.fromhex(tlv_buff)).decode()

		qr_image = io.BytesIO()
		url = qr_create(base64_string, error="L")
		url.png(qr_image, scale=2, quiet_zone=1)

		name = frappe.generate_hash(doc.name, 5)

		# making file
		filename = f"QRCode-{name}.png".replace(os.path.sep, "__")
		_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": filename,
				"is_private": 0,
				"content": qr_image.getvalue(),
				"attached_to_doctype": doc.get("doctype"),
				"attached_to_name": doc.get("name"),
				"attached_to_field": "ksa_einv_qr",
			}
		)

		_file.save()

		# assigning to document
		doc.db_set("ksa_einv_qr", _file.file_url)
		doc.notify_update()


def get_vat_amount(doc):
	vat_settings = frappe.db.get_value("KSA VAT Setting", {"company": doc.company})
	vat_accounts = []
	vat_amount = 0

	if vat_settings:
		vat_settings_doc = frappe.get_cached_doc("KSA VAT Setting", vat_settings)

		for row in vat_settings_doc.get("ksa_vat_sales_accounts"):
			vat_accounts.append(row.account)

	for tax in doc.get("taxes"):
		if tax.account_head in vat_accounts:
			vat_amount += tax.tax_amount

	return vat_amount


def delete_qr_code_file(doc, method=None):
	region = get_region(doc.company)
	if region not in ["Saudi Arabia"]:
		return

	if hasattr(doc, "ksa_einv_qr"):
		if doc.get("ksa_einv_qr"):
			file_doc = frappe.get_list("File", {"file_url": doc.get("ksa_einv_qr")})
			if len(file_doc):
				frappe.delete_doc("File", file_doc[0].name)


def delete_vat_settings_for_company(doc, method=None):
	if doc.country != "Saudi Arabia":
		return

	if frappe.db.exists("KSA VAT Setting", doc.name):
		frappe.delete_doc("KSA VAT Setting", doc.name)
