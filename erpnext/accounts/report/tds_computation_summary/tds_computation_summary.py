import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.utils import get_fiscal_year
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category \
	import get_advance_vouchers, get_debit_note_amount

def execute(filters=None):
	validate_filters(filters)

	filters.naming_series = frappe.db.get_single_value('Buying Settings', 'supp_master_name')

	columns = get_columns(filters)
	res = get_result(filters)

	return columns, res

def validate_filters(filters):
	''' Validate if dates are properly set and lie in the same fiscal year'''
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	from_year = get_fiscal_year(filters.from_date)[0]
	to_year = get_fiscal_year(filters.to_date)[0]
	if from_year != to_year:
		frappe.throw(_("From Date and To Date lie in different Fiscal Year"))

	filters["fiscal_year"] = from_year

def get_result(filters):
	# if no supplier selected, fetch data for all tds applicable supplier
	# else fetch relevant data for selected supplier
	pan = "pan" if frappe.db.has_column("Supplier", "pan") else "tax_id"
	fields = ["name", pan+" as pan", "tax_withholding_category", "supplier_type", "supplier_name"]

	if filters.supplier:
		filters.supplier = frappe.db.get_list('Supplier',
			{"name": filters.supplier}, fields)
	else:
		filters.supplier = frappe.db.get_list('Supplier',
			{"tax_withholding_category": ["!=", ""]}, fields)

	out = []
	for supplier in filters.supplier:
		tds = frappe.get_doc("Tax Withholding Category", supplier.tax_withholding_category)
		rate = [d.tax_withholding_rate for d in tds.rates if d.fiscal_year == filters.fiscal_year][0]
		try:
			account = [d.account for d in tds.accounts if d.company == filters.company][0]
		except IndexError:
			account = []
		total_invoiced_amount, tds_deducted = get_invoice_and_tds_amount(supplier.name, account,
			filters.company, filters.from_date, filters.to_date)

		if total_invoiced_amount or tds_deducted:
			row = [supplier.pan, supplier.name]

			if filters.naming_series == 'Naming Series':
				row.append(supplier.supplier_name)

			row.extend([tds.name, supplier.supplier_type, rate, total_invoiced_amount, tds_deducted])
			out.append(row)

	return out

def get_invoice_and_tds_amount(supplier, account, company, from_date, to_date):
	''' calculate total invoice amount and total tds deducted for given supplier  '''

	entries = frappe.db.sql("""
		select voucher_no, credit
		from `tabGL Entry`
		where party in (%s) and credit > 0
			and company=%s and posting_date between %s and %s
	""", (supplier, company, from_date, to_date), as_dict=1)

	supplier_credit_amount = flt(sum([d.credit for d in entries]))

	vouchers = [d.voucher_no for d in entries]
	vouchers += get_advance_vouchers(supplier, company=company,
		from_date=from_date, to_date=to_date)

	tds_deducted = 0
	if vouchers:
		tds_deducted = flt(frappe.db.sql("""
			select sum(credit)
			from `tabGL Entry`
			where account=%s and posting_date between %s and %s
				and company=%s and credit > 0 and voucher_no in ({0})
		""".format(', '.join(["'%s'" % d for d in vouchers])),
			(account, from_date, to_date, company))[0][0])

	debit_note_amount = get_debit_note_amount(supplier, from_date, to_date, company=company)

	total_invoiced_amount = supplier_credit_amount + tds_deducted - debit_note_amount

	return total_invoiced_amount, tds_deducted

def get_columns(filters):
	columns = [
		{
			"label": _("PAN"),
			"fieldname": "pan",
			"fieldtype": "Data",
			"width": 90
		},
		{
			"label": _("Supplier"),
			"options": "Supplier",
			"fieldname": "supplier",
			"fieldtype": "Link",
			"width": 180
		}]

	if filters.naming_series == 'Naming Series':
		columns.append({
			"label": _("Supplier Name"),
			"fieldname": "supplier_name",
			"fieldtype": "Data",
			"width": 180
		})

	columns.extend([
		{
			"label": _("Section Code"),
			"options": "Tax Withholding Category",
			"fieldname": "section_code",
			"fieldtype": "Link",
			"width": 180
		},
		{
			"label": _("Entity Type"),
			"fieldname": "entity_type",
			"fieldtype": "Data",
			"width": 180
		},
		{
			"label": _("TDS Rate %"),
			"fieldname": "tds_rate",
			"fieldtype": "Float",
			"width": 90
		},
		{
			"label": _("Total Amount Credited"),
			"fieldname": "total_amount_credited",
			"fieldtype": "Float",
			"width": 90
		},
		{
			"label": _("Amount of TDS Deducted"),
			"fieldname": "tds_deducted",
			"fieldtype": "Float",
			"width": 90
		}
	])

	return columns
