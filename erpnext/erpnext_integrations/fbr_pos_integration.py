import frappe
from frappe.utils import cint, flt, cstr, getdate, get_time
from frappe import _
from pyqrcode import create as qrcreate
from six import BytesIO
import datetime
import requests


def validate_fbr_pos_invoice(invoice):
	if not invoice.meta.has_field('is_fbr_pos_invoice'):
		return

	if not cint(invoice.get('has_stin')):
		invoice.is_fbr_pos_invoice = 0

	if cint(invoice.get('is_fbr_pos_invoice')):
		validate_is_fbr_pos(invoice)
	else:
		validate_not_fbr_pos(invoice)


def validate_is_fbr_pos(invoice):
	if cint(invoice.get('set_posting_time')):
		frappe.throw(_("Cannot set Posting Date/Time manually for FBR POS Invoice. Please uncheck 'Edit Posting Date and Time'"))

	if not invoice.get('fbr_pos_id'):
		invoice.fbr_pos_id = frappe.get_cached_value("FBR POS Settings", None, "default_fbr_pos_id")


def validate_not_fbr_pos(invoice):
	invoice.fbr_pos_invoice_no = None
	invoice.fbr_pos_id = None
	invoice.fbr_pos_qrcode = None


def before_cancel_fbr_pos_invoice(invoice):
	if not invoice.meta.has_field('is_fbr_pos_invoice'):
		return
	if cint(invoice.get('is_fbr_pos_invoice')):
		frappe.throw(_("Cannot cancel an FBR POS Invoice. Please make a Credit Note instead."))


def on_submit_fbr_pos_invoice(invoice):
	if not invoice.meta.has_field('is_fbr_pos_invoice'):
		return
	if not cint(invoice.get('is_fbr_pos_invoice')):
		return

	invoice_data = get_invoice_data(invoice)
	invoice_number = push_invoice_data(invoice_data)
	qrcode_svg = get_qrcode_svg(invoice_number)

	invoice.db_set({
		'fbr_pos_invoice_no': invoice_number,
		'fbr_pos_qrcode': qrcode_svg,
	})


def get_invoice_data(invoice):
	data = frappe._dict()

	return_against = invoice.return_against if cint(invoice.is_return) else None
	sales_tax_account = frappe.get_cached_value('Company', invoice.company, "sales_tax_account")
	further_tax_account = frappe.get_cached_value('Company', invoice.company, "further_tax_account")

	if not sales_tax_account:
		frappe.throw(_("Please set Sales Tax Account in {0} to get FBR POS Invoice Data")
			.format(frappe.get_desk_link("Company", invoice.company)))

	# Invoice Details
	data.InvoiceNumber = ""
	data.POSID = cint(invoice.get('fbr_pos_id'))
	data.USIN = invoice.name
	data.RefUSIN = return_against
	data.DateTime = get_posting_datetime_str(invoice)
	data.InvoiceType = get_invoice_type(invoice)
	data.PaymentMode = get_payment_mode(invoice)

	# Customer Details
	data.BuyerName = invoice.bill_to_name or invoice.customer_name
	data.BuyerNTN = invoice.tax_id
	data.BuyerCNIC = invoice.tax_cnic
	data.BuyerPhoneNumber = invoice.contact_mobile or invoice.contact_phone

	# Totals
	data.TotalQuantity = flt(invoice.total_qty)
	data.TotalSaleValue = flt(invoice.base_taxable_total, invoice.precision('base_taxable_total'))
	data.Discount = flt(invoice.base_total_discount, invoice.precision('base_total_discount'))

	data.TotalTaxCharged = 0
	data.FurtherTax = 0
	data.TotalBillAmount = 0

	# Items
	data.Items = []
	for d in invoice.items:
		item_data = frappe._dict()
		data.Items.append(item_data)

		item_data.ItemCode = d.item_code or d.item_name
		item_data.ItemName = d.item_name

		item_data.InvoiceType = get_item_invoice_type(d, invoice)
		item_data.RefUSIN = return_against
		item_data.PCTCode = frappe.get_cached_value("Item", d.item_code, "customs_tariff_number") if d.item_code else ""

		item_data.Quantity = flt(d.qty)
		item_data.SaleValue = flt(d.base_taxable_amount, d.precision('base_taxable_amount'))
		item_data.Discount = flt(d.base_tax_exclusive_total_discount, d.precision('base_tax_exclusive_total_discount'))

		# Taxes
		sales_tax_details = get_item_tax_details(d, invoice, sales_tax_account)
		further_tax_details = get_item_tax_details(d, invoice, further_tax_account)
		item_data.TaxRate = flt(sales_tax_details.rate)
		item_data.TaxCharged = flt(sales_tax_details.tax_amount_after_discount_amount)
		item_data.FurtherTax = flt(further_tax_details.tax_amount_after_discount_amount)

		item_data.TotalAmount = flt(item_data.SaleValue + item_data.TaxCharged + item_data.FurtherTax,
			d.precision('amount'))

		# Totals
		data.TotalTaxCharged += item_data.TaxCharged
		data.FurtherTax += item_data.FurtherTax
		data.TotalBillAmount += item_data.TotalAmount

	data.TotalTaxCharged = flt(data.TotalTaxCharged, invoice.precision('total_taxes_and_charges'))
	data.FurtherTax = flt(data.FurtherTax, invoice.precision('total_taxes_and_charges'))
	data.TotalBillAmount = flt(data.TotalBillAmount, invoice.precision('grand_total'))

	return data


def get_posting_datetime_str(invoice):
	posting_datetime = datetime.datetime.combine(getdate(invoice.posting_date), get_time(invoice.posting_time))
	return cstr(posting_datetime)


def get_payment_mode(invoice):
	CASH = 1
	CARD = 2
	GIFT_VOUCHER = 3
	LOYALTY_CARD = 4
	MIXED = 5
	CHEQUE = 6

	payments = invoice.get('payments') or []
	payments = [d for d in payments if flt(d.amount)]

	loyalty_points_redeemed = cint(invoice.redeem_loyalty_points) and flt(invoice.loyalty_points)

	if len(payments) == 1:
		mode_of_payment = cstr(payments[0].mode_of_payment)
		mode_type = frappe.get_cached_value("Mode of Payment", mode_of_payment, "type")

		if loyalty_points_redeemed:
			return MIXED
		elif mode_type == "Cash":
			return CASH
		elif mode_type == "Card":
			return CARD
		elif mode_type == "Cheque":
			return CHEQUE
		else:
			return MIXED

	elif len(payments) == 0 and loyalty_points_redeemed:
		return LOYALTY_CARD

	else:
		return MIXED


def get_invoice_type(invoice):
	NEW = 1
	DEBIT = 2
	CREDIT = 3

	if cint(invoice.is_return):
		return CREDIT
	else:
		return NEW


def get_item_invoice_type(item, invoice):
	NEW = 1
	CREDIT = 3
	NEW_3RD = 11
	CREDIT_3RD = 12

	if cint(invoice.is_return):
		return CREDIT_3RD if cint(item.apply_discount_after_taxes) else CREDIT
	else:
		return NEW_3RD if cint(item.apply_discount_after_taxes) else NEW


def get_item_tax_details(item, invoice, account):
	if not account:
		return frappe._dict()

	taxes = invoice.get_taxes_for_item(item)
	tax_row = [d for d in taxes if d.account_head == account]

	if not tax_row:
		return frappe._dict()
	elif len(tax_row) > 1:
		frappe.throw(_("Row #{0}: Tax Account {1} is duplicated").format(tax_row[-1].idx, account))

	return tax_row[0]


def push_invoice_data(data):
	url = frappe.get_cached_value("FBR POS Settings", None, "post_invoice_data_endpoint")
	if not url:
		frappe.throw(_("Please set 'Post Invoice Data URL' in FBR POS Settings"))

	invoice_number = None

	try:
		r = requests.post(url, json=data)
		r.raise_for_status()

		response_json = r.json()

		response_code = response_json.get('Code')
		invoice_number = response_json.get('InvoiceNumber')
		errors = response_json.get('Errors')

		if errors:
			frappe.throw(_("An error occurred while generating FBR POS Invoice:<br>{0}").format(errors))
		if not invoice_number:
			frappe.throw(_("FBR POS Invoice Number was not provided by FBR POS Service"))
	except requests.exceptions.ConnectionError:
		frappe.throw(_("Could not connect to FBR POS Service at {0}").format(url))
	except requests.exceptions.HTTPError as err:
		frappe.throw(_("An HTTP error occurred while connecting to the FBR POS Service:<br>{0}").format(err))

	return invoice_number


def get_qrcode_svg(invoice_number):
	qrcode = qrcreate(invoice_number)
	svg = ''
	stream = BytesIO()
	try:
		qrcode.svg(stream, scale=2, background="#fff", module_color="#000", quiet_zone=1, omithw=True)
		svg = stream.getvalue().decode().replace('\n', '')
	finally:
		stream.close()

	return svg
