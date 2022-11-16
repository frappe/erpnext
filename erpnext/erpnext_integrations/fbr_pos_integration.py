import frappe
from frappe.utils import cint, flt, cstr, getdate, get_time
from frappe import _
from pyqrcode import create as qrcreate
from six import BytesIO
from frappe.exceptions import ValidationError
import json
import datetime
import requests


class FBRPOSRequestError(ValidationError):
	pass


class FBRPOSConnectionError(FBRPOSRequestError):
	pass


class FBRPOSResponseError(FBRPOSRequestError):
	pass


def validate_fbr_pos_invoice(invoice):
	if not invoice.meta.has_field('is_fbr_pos_invoice'):
		return

	# Reset values for draft
	if invoice.docstatus == 0:
		reset_values_for_draft_invoice(invoice)

	# Determine if FBR POS Invoice
	invoice.is_fbr_pos_invoice = determine_is_fbr_pos(invoice)

	# Calculate FBR POS Invoice and Item Values
	if cint(invoice.get('is_fbr_pos_invoice')):
		calculate_fbr_pos_values(invoice)

	# If no FBR POS Items, not an FBR POS
	if not invoice.get('fbr_pos_items'):
		invoice.is_fbr_pos_invoice = 0
	# If no taxes charged or no taxable
	if not any([d.fbr_pos_sale_value or d.fbr_pos_tax_charged for d in invoice.get('fbr_pos_items')]):
		invoice.is_fbr_pos_invoice = 0

	if cint(invoice.get('is_fbr_pos_invoice')):
		# Validate FBR POS
		validate_is_fbr_pos(invoice)
	else:
		# Not an FBR POS Reset Values
		reset_values_for_not_fbr_pos(invoice)


def determine_is_fbr_pos(invoice):
	enable_fbr_pos = cint(frappe.get_cached_value("FBR POS Settings", None, "enable_fbr_pos"))

	if enable_fbr_pos and cint(invoice.get('has_stin')):
		return 1
	else:
		return 0


def check_fbr_pos_enabled(throw=False):
	if not cint(frappe.conf.get('enable_fbr_pos')):
		if throw:
			frappe.throw(_("FBR POS is not enabled from the backend. Please contact your system administrator."))
		return False

	if not cint(frappe.db.get_single_value("FBR POS Settings", "enable_fbr_pos")):
		if throw:
			frappe.throw(_("FBR POS is not enabled from FBR POS Settings. Please contact your system administrator."))
		return False

	return True


def validate_is_fbr_pos(invoice):
	if cint(invoice.get('set_posting_time')):
		frappe.throw(_("Cannot set Posting Date/Time manually for FBR POS Invoice. Please uncheck 'Edit Posting Date and Time'"))

	if not invoice.get('fbr_pos_id'):
		invoice.fbr_pos_id = frappe.get_cached_value("FBR POS Settings", None, "default_fbr_pos_id")


def reset_values_for_draft_invoice(invoice):
	invoice.fbr_pos_invoice_no = None
	invoice.fbr_pos_qrcode = None
	invoice.fbr_pos_json_data = None


def reset_values_for_not_fbr_pos(invoice):
	invoice.fbr_pos_invoice_no = None
	invoice.fbr_pos_id = None
	invoice.fbr_pos_qrcode = None
	invoice.fbr_pos_json_data = None
	invoice.fbr_pos_invoice_type = None
	invoice.fbr_pos_payment_mode = None
	invoice.fbr_pos_total_sale_value = 0
	invoice.fbr_pos_discount = 0
	invoice.fbr_pos_total_quantity = 0
	invoice.fbr_pos_total_tax_charged = 0
	invoice.fbr_pos_further_tax = 0
	invoice.fbr_pos_total_bill_amount = 0
	invoice.fbr_pos_items = []


def before_cancel_fbr_pos_invoice(invoice):
	if not invoice.meta.has_field('is_fbr_pos_invoice'):
		return
	if cint(invoice.get('is_fbr_pos_invoice')) and invoice.get('fbr_pos_invoice_no'):
		if frappe.conf.get('allow_fbr_pos_cancellation') and not check_fbr_pos_enabled() and frappe.conf.get("developer_mode"):
			# Allow cancelling ONLY if explicity allowed to cancel and FBR POS not enabled and in developer mode
			pass
		else:
			frappe.throw(_("Cannot cancel FBR POS Invoice because it is already posted. Please make a Credit Note instead."))


def on_submit_fbr_pos_invoice(invoice):
	if not check_fbr_pos_enabled():
		return

	ignore_connection_error = cint(frappe.get_cached_value("FBR POS Settings", None, "ignore_connection_error_on_submit"))
	post_fbr_pos_invoice(invoice, ignore_connection_error=ignore_connection_error)
	if frappe.flags.fbr_pos_connection_error:
		frappe.msgprint(_(
			"FBR POS Invoice Number could not be generated because of a connection error to the FBR POS Service.<br><br>"
			"System will attempt to generate FBR POS Invoice Number again in the background. "
			"You can also retry manually by clicking the 'Sync FBR POS Invoice' button."
		), title=_("FBR POS Service Connection Failed"))


# called by scheduler
def post_fbr_pos_invoices_without_number():
	if not check_fbr_pos_enabled():
		return

	failed_invoices = frappe.db.sql_list("""
		select name
		from `tabSales Invoice`
		where docstatus = 1 and is_fbr_pos_invoice = 1 and (fbr_pos_invoice_no = '' or fbr_pos_invoice_no is null)
		order by posting_date, posting_time, creation
		limit 100
		for update
	""")

	for name in failed_invoices:
		invoice = frappe.get_doc("Sales Invoice", name)
		try:
			post_fbr_pos_invoice(invoice)
		except FBRPOSRequestError:
			pass
		except Exception:
			frappe.log_error(message=frappe.as_unicode(frappe.get_traceback()), title=get_error_title(invoice.name),
				reference_doctype="Sales Invoice", reference_name=name)


def calculate_fbr_pos_values(invoice):
	sales_tax_account = frappe.get_cached_value('Company', invoice.company, "sales_tax_account")
	further_tax_account = frappe.get_cached_value('Company', invoice.company, "further_tax_account")

	if not sales_tax_account:
		frappe.throw(_("Please set Sales Tax Account in {0} to calculate FBR POS Invoice Data")
			.format(frappe.get_desk_link("Company", invoice.company)))

	invoice.fbr_pos_invoice_type = get_invoice_type(invoice, as_str=True)
	invoice.fbr_pos_payment_mode = get_payment_mode(invoice, as_str=True)

	# Set Totals as Zero for Accumulation
	invoice.fbr_pos_total_quantity = 0
	invoice.fbr_pos_total_sale_value = 0
	invoice.fbr_pos_discount = 0

	invoice.fbr_pos_total_tax_charged = 0
	invoice.fbr_pos_further_tax = 0
	invoice.fbr_pos_total_bill_amount = 0

	# Create Item Row ID Map
	item_map = {}
	existing_pos_item_map = {}
	for d in invoice.items:
		item_map[d.name] = d
	for d in invoice.get('fbr_pos_items'):
		if d.fbr_pos_item_reference:
			existing_pos_item_map[d.fbr_pos_item_reference] = d

	# Items
	invoice.fbr_pos_items = []
	for item in invoice.items:
		existing_pos_item = existing_pos_item_map.get(item.name)
		pos_item = invoice.append('fbr_pos_items', existing_pos_item)

		# Reference to line item
		pos_item.fbr_pos_item_reference = item.name

		# Item Code
		pos_item.fbr_pos_item_code = item.item_code or item.item_name
		pos_item.fbr_pos_item_name = item.item_name

		# Item/Transaction Type
		pos_item.fbr_pos_invoice_type = get_item_invoice_type(item, invoice, as_str=True)
		pos_item.fbr_pos_pct_code = get_item_pct_code(item)

		# Amounts
		pos_item.fbr_pos_quantity = flt(item.qty, pos_item.precision('fbr_pos_quantity'))
		pos_item.fbr_pos_sale_value = flt(item.base_taxable_amount, pos_item.precision('fbr_pos_sale_value'))
		pos_item.fbr_pos_discount = flt(item.base_tax_exclusive_total_discount, pos_item.precision('fbr_pos_discount'))

		# Taxes
		sales_tax_details = get_item_tax_details(item, invoice, sales_tax_account)
		further_tax_details = get_item_tax_details(item, invoice, further_tax_account)

		pos_item.fbr_pos_tax_rate = flt(sales_tax_details.rate, pos_item.precision('fbr_pos_tax_rate'))
		pos_item.fbr_pos_tax_charged = flt(sales_tax_details.tax_amount_after_discount_amount,
			pos_item.precision('fbr_pos_tax_charged'))
		pos_item.fbr_pos_further_tax = flt(further_tax_details.tax_amount_after_discount_amount,
			pos_item.precision('fbr_pos_further_tax'))

		pos_item.fbr_pos_total_amount = flt(pos_item.fbr_pos_sale_value + pos_item.fbr_pos_tax_charged + pos_item.fbr_pos_further_tax,
			pos_item.precision('fbr_pos_total_amount'))

		# Add to Totals
		if pos_item.fbr_pos_tax_rate or pos_item.fbr_pos_tax_charged or pos_item.fbr_pos_further_tax:
			invoice.fbr_pos_total_quantity += pos_item.fbr_pos_quantity
			invoice.fbr_pos_total_sale_value += pos_item.fbr_pos_sale_value
			invoice.fbr_pos_discount += pos_item.fbr_pos_discount

			invoice.fbr_pos_total_tax_charged += pos_item.fbr_pos_tax_charged
			invoice.fbr_pos_further_tax += pos_item.fbr_pos_further_tax
			invoice.fbr_pos_total_bill_amount += pos_item.fbr_pos_total_amount
		else:
			invoice.remove(pos_item)

	for i, pos_item in enumerate(invoice.fbr_pos_items):
		pos_item.idx = i + 1

	# Round Totals
	invoice.fbr_pos_total_quantity = flt(invoice.fbr_pos_total_quantity, invoice.precision('fbr_pos_total_quantity'))
	invoice.fbr_pos_total_sale_value = flt(invoice.fbr_pos_total_sale_value, invoice.precision('fbr_pos_total_sale_value'))
	invoice.fbr_pos_discount = flt(invoice.fbr_pos_discount, invoice.precision('fbr_pos_discount'))

	invoice.fbr_pos_total_tax_charged = flt(invoice.fbr_pos_total_tax_charged, invoice.precision('fbr_pos_total_tax_charged'))
	invoice.fbr_pos_further_tax = flt(invoice.fbr_pos_further_tax, invoice.precision('fbr_pos_further_tax'))
	invoice.fbr_pos_total_bill_amount = flt(invoice.fbr_pos_total_bill_amount, invoice.precision('fbr_pos_total_bill_amount'))


def get_invoice_data(invoice):
	invoice_data = frappe._dict()

	return_against = invoice.return_against if cint(invoice.is_return) else None

	# Invoice Details
	invoice_data.InvoiceNumber = ""
	invoice_data.POSID = cint(invoice.get('fbr_pos_id'))
	invoice_data.USIN = invoice.name
	invoice_data.RefUSIN = return_against
	invoice_data.DateTime = get_posting_datetime_str(invoice)
	invoice_data.InvoiceType = get_invoice_type(invoice)
	invoice_data.PaymentMode = get_payment_mode(invoice)

	# Customer Details
	invoice_data.BuyerName = invoice.bill_to_name or invoice.customer_name
	invoice_data.BuyerNTN = invoice.tax_id
	invoice_data.BuyerCNIC = invoice.tax_cnic
	invoice_data.BuyerPhoneNumber = invoice.contact_mobile or invoice.contact_phone

	# Totals
	invoice_data.TotalQuantity = flt(invoice.fbr_pos_total_quantity)
	invoice_data.TotalSaleValue = flt(invoice.fbr_pos_total_sale_value)
	invoice_data.Discount = flt(invoice.fbr_pos_discount)

	invoice_data.TotalTaxCharged = flt(invoice.fbr_pos_total_tax_charged)
	invoice_data.FurtherTax = flt(invoice.fbr_pos_further_tax)
	invoice_data.TotalBillAmount = flt(invoice.fbr_pos_total_bill_amount)

	# Items
	invoice_data.Items = []
	for pos_item in invoice.fbr_pos_items:
		item_data = frappe._dict()
		invoice_data.Items.append(item_data)

		item = invoice.getone('items', {'name': pos_item.fbr_pos_item_reference})
		if not item:
			frappe.throw(_("Could not find reference to line item FBR POS Item Row #{0} Item Code {1}").format(pos_item.idx, pos_item.item_code))

		item_data.ItemCode = pos_item.fbr_pos_item_code
		item_data.ItemName = pos_item.fbr_pos_item_name

		item_data.InvoiceType = get_item_invoice_type(item, invoice)
		item_data.RefUSIN = return_against
		item_data.PCTCode = pos_item.fbr_pos_pct_code

		item_data.Quantity = flt(pos_item.fbr_pos_quantity)
		item_data.SaleValue = flt(pos_item.fbr_pos_sale_value)
		item_data.Discount = flt(pos_item.fbr_pos_discount)

		# Taxes
		item_data.TaxRate = flt(pos_item.fbr_pos_tax_rate)
		item_data.TaxCharged = flt(pos_item.fbr_pos_tax_charged)
		item_data.FurtherTax = flt(pos_item.fbr_pos_further_tax)

		item_data.TotalAmount = flt(pos_item.fbr_pos_total_amount)

	return invoice_data


def get_posting_datetime_str(invoice):
	posting_datetime = datetime.datetime.combine(getdate(invoice.posting_date), get_time(invoice.posting_time))
	return cstr(posting_datetime)


def get_payment_mode(invoice, as_str=False):
	values = frappe._dict({
		'CASH': 1,
		'CARD': 2,
		'GIFT_VOUCHER': 3,
		'LOYALTY_CARD': 4,
		'MIXED': 5,
		'CHEQUE': 6,
	})

	payments = invoice.get('payments') or []
	payments = [d for d in payments if flt(d.amount)]

	loyalty_points_redeemed = cint(invoice.redeem_loyalty_points) and flt(invoice.loyalty_points)

	if len(payments) == 1:
		mode_of_payment = cstr(payments[0].mode_of_payment)
		mode_type = frappe.get_cached_value("Mode of Payment", mode_of_payment, "type")

		if loyalty_points_redeemed:
			key = 'MIXED'
		elif mode_type == "Cash":
			key = 'CASH'
		elif mode_type == "Card":
			key = 'CARD'
		elif mode_type == "Cheque":
			key = 'CHEQUE'
		else:
			key = 'MIXED'

	elif len(payments) == 0 and loyalty_points_redeemed:
		key = 'LOYALTY_CARD'

	else:
		key = 'MIXED'

	if as_str:
		return key
	else:
		return values[key]


def get_invoice_type(invoice, as_str=False):
	values = frappe._dict({
		'NEW': 1,
		'DEBIT': 2,
		'CREDIT': 3,
	})

	if cint(invoice.is_return):
		key = 'CREDIT'
	else:
		key = 'NEW'

	if as_str:
		return key
	else:
		return values[key]


def get_item_invoice_type(item, invoice, as_str=False):
	values = frappe._dict({
		'NEW': 1,
		'CREDIT': 3,
		'NEW_3RD': 11,
		'CREDIT_3RD': 12,
	})

	if cint(invoice.is_return):
		key = 'CREDIT_3RD' if cint(item.apply_discount_after_taxes) else 'CREDIT'
	else:
		key = 'NEW_3RD' if cint(item.apply_discount_after_taxes) else 'NEW'

	if as_str:
		return key
	else:
		return values[key]


def get_item_pct_code(item):
	if item.item_code:
		pct_code = frappe.get_cached_value("Item", item.item_code, "customs_tariff_number")
		if pct_code:
			return pct_code
		else:
			return get_item_group_pct_code(frappe.get_cached_value("Item", item.item_code, "item_group"))
	else:
		return None


def get_item_group_pct_code(item_group):
	current_item_group = item_group
	while current_item_group:
		item_group_doc = frappe.get_cached_doc("Item Group", current_item_group)
		if item_group_doc.customs_tariff_number:
			return item_group_doc.customs_tariff_number

		current_item_group = item_group_doc.parent_item_group

	return None


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


@frappe.whitelist()
def sync_fbr_pos_invoice(sales_invoice):
	check_fbr_pos_enabled(throw=True)

	invoice = frappe.get_doc("Sales Invoice", sales_invoice)
	invoice.check_permission("submit")

	invoice_number = post_fbr_pos_invoice(invoice)
	if invoice_number:
		frappe.msgprint(_("FBR POS Invoice Number {0} generated for Sales Invoice {1}")
			.format(frappe.bold(invoice_number), invoice.name))
	else:
		frappe.msgprint(_("FBR POS Invoice Number could not be generated"))

	return invoice_number


def post_fbr_pos_invoice(invoice, ignore_connection_error=False):
	if not check_fbr_pos_enabled():
		return
	if not invoice.meta.has_field('is_fbr_pos_invoice'):
		return
	if not cint(invoice.get('is_fbr_pos_invoice')):
		return
	if invoice.docstatus != 1:
		return
	if invoice.fbr_pos_invoice_no:
		return

	invoice_data = get_invoice_data(invoice)
	json_data = json.dumps(invoice_data)

	invoice_number = push_invoice_data(invoice_data, invoice.name, ignore_connection_error=ignore_connection_error)

	if invoice_number:
		qrcode_svg = get_qrcode_svg(invoice_number)

		invoice.db_set({
			'fbr_pos_invoice_no': invoice_number,
			'fbr_pos_qrcode': qrcode_svg,
			'fbr_pos_json_data': json_data,
		})

		invoice.notify_update()

	return invoice_number


def push_invoice_data(data, sales_invoice, ignore_connection_error=False):
	invoice_number = None

	fbr_pos_settings = frappe.get_cached_doc("FBR POS Settings", None)

	url = fbr_pos_settings.post_invoice_data_endpoint
	if not url:
		frappe.throw(_("Please set 'Post Invoice Data URL' in FBR POS Settings"))

	headers = {"Content-Type": "application/json"}
	auth_token = fbr_pos_settings.post_invoice_auth_token
	if auth_token:
		headers["Authorization"] = "Bearer {0}".format(auth_token)

	try:
		r = requests.post(url, json=data, headers=headers, timeout=10)
		r.raise_for_status()

		response_json = r.json()

		response_code = response_json.get('Code')
		response_message = response_json.get('Response')
		invoice_number = response_json.get('InvoiceNumber')
		errors = response_json.get('Errors')

		response_html = "<br><br>{0}".format(response_message) if response_message else ""

		if errors:
			log_fbr_pos_request("Error", sales_invoice, data, invoice_number, r, error_type="FBR POS Error")
			frappe.throw(_("An error occurred while generating <b>FBR POS Invoice</b>:<br>{0}{1}")
				.format(errors, response_html), exc=FBRPOSResponseError)

		if response_code != '100':
			log_fbr_pos_request("Error", sales_invoice, data, invoice_number, r, error_type="Invalid Response Code")
			frappe.throw(_("Received an invalid response while generating <b>FBR POS Invoice</b>{0}")
				.format(response_html), exc=FBRPOSResponseError)

		if not invoice_number or invoice_number == 'Not Available':
			log_fbr_pos_request("Error", sales_invoice, data, invoice_number, r, error_type="Invoice Number Not Available")
			frappe.throw(_("FBR POS Invoice Number was not provided by <b>FBR POS Service</b>"), exc=FBRPOSResponseError)

	except requests.exceptions.ConnectionError as err:
		log_fbr_pos_request("Error", sales_invoice, data, invoice_number, error_type="Connection Error")
		frappe.flags.fbr_pos_connection_error = True
		if not ignore_connection_error:
			frappe.throw(_("Could not connect to <b>FBR POS Service</b>:<br>{0}").format(err), exc=FBRPOSConnectionError)

	except requests.exceptions.Timeout as err:
		log_fbr_pos_request("Error", sales_invoice, data, invoice_number, error_type="Connection Timeout")
		frappe.flags.fbr_pos_connection_error = True
		if not ignore_connection_error:
			frappe.throw(_("Connection to <b>FBR POS Service</b> timed out:<br>{0}").format(err), exc=FBRPOSConnectionError)

	except requests.exceptions.HTTPError as err:
		log_fbr_pos_request("Error", sales_invoice, data, invoice_number, error_type="HTTP Error")
		frappe.flags.fbr_pos_connection_error = True
		if not ignore_connection_error:
			frappe.throw(_("An HTTP error occurred while connecting to the <b>FBR POS Service</b>:<br>{0}").format(err), exc=FBRPOSConnectionError)

	except requests.exceptions.RequestException as err:
		log_fbr_pos_request("Error", sales_invoice, data, invoice_number, error_type="Request Error")
		frappe.flags.fbr_pos_connection_error = True
		if not ignore_connection_error:
			frappe.throw(_("Request to <b>FBR POS Service</b> failed:<br>{0}").format(err), exc=FBRPOSConnectionError)

	else:
		log_fbr_pos_request("Success", sales_invoice, data, invoice_number, r)

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


def log_fbr_pos_request(log_type, sales_invoice, invoice_data,
		fbr_pos_invoice_no=None, response=None, error_type=None):
	if isinstance(invoice_data, dict):
		invoice_data = json.dumps(invoice_data)

	request_timestamp = frappe.utils.now_datetime()

	error = None
	if log_type == "Error":
		error = frappe.as_unicode(frappe.get_traceback())

	frappe.enqueue("erpnext.erpnext_integrations.fbr_pos_integration.insert_fbr_pos_log",
		log_type=log_type, sales_invoice=sales_invoice, invoice_data=invoice_data,
		fbr_pos_invoice_no=fbr_pos_invoice_no,
		response_json=response.text if response else None,
		response_status_code=response.status_code if response else None,
		request_timestamp=request_timestamp,
		error_type=error_type, error=error)


def insert_fbr_pos_log(log_type, sales_invoice, invoice_data,
		fbr_pos_invoice_no=None, response_json=None, response_status_code=None, request_timestamp=None,
		error=None, error_type=None):
	log_doc = frappe.new_doc("FBR POS Log")
	log_doc.log_type = log_type
	log_doc.sales_invoice = sales_invoice
	log_doc.invoice_data = invoice_data
	log_doc.fbr_pos_invoice_no = fbr_pos_invoice_no or None
	log_doc.response = response_json
	log_doc.response_status_code = response_status_code
	log_doc.request_timestamp = request_timestamp or frappe.utils.now_datetime()
	log_doc.error = error
	log_doc.error_type = error_type

	log_doc.insert(ignore_permissions=True)


def get_error_title(invoice_name):
	return "FBR POS Invoice {0} Failed".format(invoice_name)
