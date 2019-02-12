from __future__ import unicode_literals
import frappe
from erpnext import get_company_currency, get_default_company
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.doctype.fiscal_year.fiscal_year import get_from_and_to_date
from frappe.utils import cint, get_datetime_str, formatdate, flt

__exchange_rates = {}
P_OR_L_ACCOUNTS = list(
	sum(frappe.get_list('Account', fields=['name'], or_filters=[{'root_type': 'Income'}, {'root_type': 'Expense'}], as_list=True), ())
)


def get_currency(filters):
	"""
	Returns a dictionary containing currency information. The keys of the dict are
	- company: The company for which we are fetching currency information. if no
	company is specified, it will fallback to the default company.
	- company currency: The functional currency of the said company.
	- presentation currency: The presentation currency to use. Only currencies that
	have been used for transactions will be allowed.
	- report date: The report date.
	:param filters: Report filters
	:type filters: dict

	:return: str - Currency
	"""
	company = get_appropriate_company(filters)
	company_currency = get_company_currency(company)
	presentation_currency = filters['presentation_currency'] if filters.get('presentation_currency') else company_currency

	report_date = filters.get('to_date')

	if not report_date:
		fiscal_year_to_date = get_from_and_to_date(filters.get('to_fiscal_year'))["to_date"]
		report_date = formatdate(get_datetime_str(fiscal_year_to_date), "dd-MM-yyyy")

	currency_map = dict(company=company, company_currency=company_currency, presentation_currency=presentation_currency, report_date=report_date)

	return currency_map


def convert(value, from_, to, date):
	"""
	convert `value` from `from_` to `to` on `date`
	:param value: Amount to be converted
	:param from_: Currency of `value`
	:param to: Currency to convert to
	:param date: exchange rate as at this date
	:return: Result of converting `value`
	"""
	rate = get_rate_as_at(date, from_, to)
	converted_value = flt(value) / (rate or 1)
	return converted_value


def get_rate_as_at(date, from_currency, to_currency):
	"""
	Gets exchange rate as at `date` for `from_currency` - `to_currency` exchange rate.
	This calls `get_exchange_rate` so that we can get the correct exchange rate as per
	the user's Accounts Settings.
	It is made efficient by memoising results to `__exchange_rates`
	:param date: exchange rate as at this date
	:param from_currency: Base currency
	:param to_currency: Quote currency
	:return: Retrieved exchange rate
	"""

	rate = __exchange_rates.get('{0}-{1}@{2}'.format(from_currency, to_currency, date))
	if not rate:
		rate = get_exchange_rate(from_currency, to_currency, date) or 1
		__exchange_rates['{0}-{1}@{2}'.format(from_currency, to_currency, date)] = rate

	return rate


def is_p_or_l_account(account_name):
	"""
	Check if the given `account name` is an `Account` with `root_type` of either 'Income'
	or 'Expense'.
	:param account_name:
	:return: Boolean
	"""
	return account_name in P_OR_L_ACCOUNTS


def convert_to_presentation_currency(gl_entries, currency_info):
	"""
	Take a list of GL Entries and change the 'debit' and 'credit' values to currencies
	in `currency_info`.
	:param gl_entries:
	:param currency_info:
	:return:
	"""
	converted_gl_list = []
	presentation_currency = currency_info['presentation_currency']
	company_currency = currency_info['company_currency']

	for entry in gl_entries:
		account = entry['account']
		debit = flt(entry['debit'])
		credit = flt(entry['credit'])
		debit_in_account_currency = flt(entry['debit_in_account_currency'])
		credit_in_account_currency = flt(entry['credit_in_account_currency'])
		account_currency = entry['account_currency']

		if account_currency != presentation_currency:
			value = debit or credit

			date = currency_info['report_date'] if not is_p_or_l_account(account) else entry['posting_date']
			converted_value = convert(value, presentation_currency, company_currency, date)

			if entry.get('debit'):
				entry['debit'] = converted_value
			else:
				entry['credit'] = converted_value

		elif account_currency == presentation_currency:
			if entry.get('debit'):
				entry['debit'] = debit_in_account_currency
			else:
				entry['credit'] = credit_in_account_currency

		converted_gl_list.append(entry)

	return converted_gl_list


def get_appropriate_company(filters):
	if filters.get('company'):
		company = filters['company']
	else:
		company = get_default_company()

	return company
