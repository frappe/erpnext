import frappe
from frappe.utils import getdate
from frappe.utils.nestedset import get_descendants_of

from erpnext.accounts.utils import get_fiscal_year
from erpnext.setup.utils import get_exchange_rate


def execute():
	set_company_reporting_currency()
	set_amounts_in_reporting_currency_on_gle_and_acb()


def set_company_reporting_currency():
	root_companies = frappe.db.get_all(
		"Company", fields=["name", "default_currency"], filters={"parent_company": ""}, order_by="lft"
	)

	for d in root_companies:
		company_subtree = get_descendants_of("Company", d.name)
		company_subtree.append(d.name)

		update_company_subtree_reporting_currency(company_subtree, d.default_currency)


def update_company_subtree_reporting_currency(companies, currency):
	Company = frappe.qb.DocType("Company")

	frappe.qb.update(Company).set(Company.reporting_currency, currency).where(
		Company.name.isin(companies)
	).run()


def set_amounts_in_reporting_currency_on_gle_and_acb():
	# get all the companies
	companies = frappe.db.get_all(
		"Company", fields=["name", "default_currency", "reporting_currency"], order_by="lft"
	)

	# get current fiscal year
	current_fiscal_year = get_fiscal_year(getdate(), as_dict=1, raise_on_missing=False)

	if not current_fiscal_year:
		return

	previous_fiscal_year = frappe.db.get_value(
		"Fiscal Year",
		filters={"year_end_date": ("<", current_fiscal_year.year_start_date)},
		fieldname=["name", "year_start_date", "year_end_date"],
		order_by="year_end_date desc",
		as_dict=1,
	)

	for d in companies:
		posting_dates = get_posting_closing_date(d, current_fiscal_year, previous_fiscal_year)
		exchange_rate_available = check_exchange_rate_availability(d, posting_dates)
		if not exchange_rate_available:
			continue
		set_reporting_currency_by_doctype("GL Entry", d, posting_dates.get("GL Entry"))

		set_reporting_currency_by_doctype(
			"Account Closing Balance", d, posting_dates.get("Account Closing Balance")
		)


def get_posting_closing_date(company_details, current_fiscal_year, previous_fiscal_year=None):
	posting_dates = {}
	posting_dates["GL Entry"] = get_closing_posting_dates(
		"GL Entry", company_details.get("name"), current_fiscal_year
	)

	posting_dates["Account Closing Balance"] = get_closing_posting_dates(
		"Account Closing Balance", company_details.get("name"), current_fiscal_year
	)

	if previous_fiscal_year:
		prev_fy_last_pcv_closing_date = frappe.db.get_value(
			"Period Closing Voucher",
			filters={"fiscal_year": previous_fiscal_year.name, "company": company_details.get("name")},
			fieldname=["transaction_date"],
			order_by="period_start_date desc",
		)

		if prev_fy_last_pcv_closing_date:
			prev_fy_acb_closing_dates = get_closing_posting_dates(
				"Account Closing Balance",
				company_details.get("name"),
				closing_date=prev_fy_last_pcv_closing_date,
			)
			posting_dates.setdefault("Account Closing Balance", [])
			posting_dates["Account Closing Balance"].extend(prev_fy_acb_closing_dates)

	return posting_dates


def check_exchange_rate_availability(company_details, posting_dates):
	exchange_rate_available = True
	for doctype, values in posting_dates.items():
		if not exchange_rate_available:
			return False
		date_column = "posting_date" if doctype == "GL Entry" else "closing_date"
		for d in values:
			exchange_rate = get_exchange_rate(
				company_details.get("default_currency"),
				company_details.get("reporting_currency"),
				d[date_column],
			)

			if not exchange_rate:
				exchange_rate_available = False
				break

	return exchange_rate_available


def set_reporting_currency_by_doctype(doctype, company_details, posting_closing_dates):
	date_column = "posting_date" if doctype == "GL Entry" else "closing_date"
	for d in posting_closing_dates:
		exchange_rate = get_exchange_rate(
			company_details.get("default_currency"),
			company_details.get("reporting_currency"),
			d[date_column],
		)

		set_reporting_currency_on_individual_documents(
			doctype, company_details.get("name"), d[date_column], exchange_rate
		)


def get_closing_posting_dates(doctype, company, fiscal_year=None, closing_date=None):
	dt = frappe.qb.DocType(doctype)

	date_column = "posting_date" if doctype == "GL Entry" else "closing_date"
	query = frappe.qb.from_(dt).select(dt[date_column]).where(dt.company == company).groupby(dt[date_column])

	if doctype == "GL Entry" and fiscal_year:
		query = query.where(dt.fiscal_year == fiscal_year.name)

	if doctype == "Account Closing Balance":
		if fiscal_year:
			query = query.where(dt.closing_date[fiscal_year.year_start_date : fiscal_year.year_end_date])
		if closing_date:
			query = query.where(dt.closing_date == closing_date)

	posting_closing_dates = query.run(as_dict=1)

	return posting_closing_dates


def set_reporting_currency_on_individual_documents(doctype, company, posting_closing_date, exchange_rate):
	dt = frappe.qb.DocType(doctype)

	date_column = "posting_date" if doctype == "GL Entry" else "closing_date"

	frappe.qb.update(dt).set(dt.reporting_currency_exchange_rate, exchange_rate).set(
		dt.debit_in_reporting_currency, exchange_rate * dt.debit
	).set(dt.credit_in_reporting_currency, exchange_rate * dt.credit).where(
		(dt.company == company) & (dt[date_column] == posting_closing_date)
	).run()
