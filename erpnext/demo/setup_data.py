from __future__ import unicode_literals

import random, json
from erpnext.demo.domains import data
import frappe, erpnext
import frappe.utils

def setup_data():
	domain = frappe.flags.domain
	complete_setup(domain)
	setup_demo_page()
	setup_fiscal_year()
	setup_holiday_list()
	setup_customer()
	setup_supplier()
	setup_item()
	setup_warehouse()
	import_json('Address')
	import_json('Contact')
	setup_workstation()
	import_json('Operation')
	import_json('Lead')
	setup_item_price()
	show_item_groups_in_website()
	setup_currency_exchange()
	import_json('BOM', submit=True)
	setup_user()
	setup_employee()
	setup_salary_structure()
	setup_user_roles()
	frappe.db.commit()
	frappe.clear_cache()

def complete_setup(domain='Manufacturing'):
	print "Complete Setup..."
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	if not frappe.get_all('Company', limit=1):
		setup_complete({
			"first_name": "Test",
			"last_name": "User",
			"email": "test_demo@erpnext.com",
			"company_tagline": 'Awesome Products and Services',
			"password": "test",
			"fy_start_date": "2015-01-01",
			"fy_end_date": "2015-12-31",
			"bank_account": "National Bank",
			"industry": domain,
			"company_name": data.get(domain).get('company_name'),
			"chart_of_accounts": "Standard",
			"company_abbr": ''.join([d[0] for d in data.get(domain).get('company_name').split()]).upper(),
			"currency": 'USD',
			"timezone": 'America/New_York',
			"country": 'United States',
			"language": "english"
		})

def setup_demo_page():
	# home page should always be "start"
	website_settings = frappe.get_doc("Website Settings", "Website Settings")
	website_settings.home_page = "demo"
	website_settings.save()

def setup_fiscal_year():
	fiscal_year = None
	for year in xrange(2014, frappe.utils.now_datetime().year + 1, 1):
		try:
			fiscal_year = frappe.get_doc({
				"doctype": "Fiscal Year",
				"year": frappe.utils.cstr(year),
				"year_start_date": "{0}-01-01".format(year),
				"year_end_date": "{0}-12-31".format(year)
			}).insert()
		except frappe.DuplicateEntryError:
			pass

	# set the last fiscal year (current year) as default
	fiscal_year.set_as_default()

def setup_holiday_list():
	"""Setup Holiday List for the current year"""
	year = frappe.utils.now_datetime().year
	holiday_list = frappe.get_doc({
		"doctype": "Holiday List",
		"holiday_list_name": str(year),
		"from_date": "{0}-01-01".format(year),
		"to_date": "{0}-12-31".format(year),
	})
	holiday_list.insert()
	holiday_list.weekly_off = "Saturday"
	holiday_list.get_weekly_off_dates()
	holiday_list.weekly_off = "Sunday"
	holiday_list.get_weekly_off_dates()
	holiday_list.save()

	frappe.set_value("Company", erpnext.get_default_company(), "default_holiday_list", holiday_list.name)

def setup_customer():
	customers = [u'Asian Junction', u'Life Plan Counselling', u'Two Pesos', u'Mr Fables', u'Intelacard', u'Big D Supermarkets', u'Adaptas', u'Nelson Brothers', u'Landskip Yard Care', u'Buttrey Food & Drug', u'Fayva', u'Asian Fusion', u'Crafts Canada', u'Consumers and Consumers Express', u'Netobill', u'Choices', u'Chi-Chis', u'Red Food', u'Endicott Shoes', u'Hind Enterprises']
	for c in customers:
		frappe.get_doc({
			"doctype": "Customer",
			"customer_name": c,
			"customer_group": "Commercial",
			"customer_type": random.choice(["Company", "Individual"]),
			"territory": "Rest Of The World"
		}).insert()

def setup_supplier():
	suppliers = [u'Helios Air', u'Ks Merchandise', u'HomeBase', u'Scott Ties', u'Reliable Investments', u'Nan Duskin', u'Rainbow Records', u'New World Realty', u'Asiatic Solutions', u'Eagle Hardware', u'Modern Electricals']
	for s in suppliers:
		frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": s,
			"supplier_type": random.choice(["Services", "Raw Material"]),
		}).insert()

def setup_workstation():
	workstations = [u'Drilling Machine 1', u'Lathe 1', u'Assembly Station 1', u'Assembly Station 2', u'Packing and Testing Station']
	for w in workstations:
		frappe.get_doc({
			"doctype": "Workstation",
			"workstation_name": w,
			"holiday_list": frappe.get_all("Holiday List")[0].name,
			"hour_rate_consumable": int(random.random() * 20),
			"hour_rate_electricity": int(random.random() * 10),
			"hour_rate_labour": int(random.random() * 40),
			"hour_rate_rent": int(random.random() * 10),
			"working_hours": [
				{
					"enabled": 1,
				    "start_time": "8:00:00",
					"end_time": "15:00:00"
				}
			]
		}).insert()

def show_item_groups_in_website():
	"""set show_in_website=1 for Item Groups"""
	products = frappe.get_doc("Item Group", "Products")
	products.show_in_website = 1
	products.route = 'products'
	products.save()

def setup_item():
	items = json.loads(open(frappe.get_app_path('erpnext', 'demo', 'data', 'item.json')).read())
	for i in items:
		item = frappe.new_doc('Item')
		item.update(i)
		item.min_order_qty = random.randint(10, 30)
		item.default_warehouse = frappe.get_all('Warehouse', filters={'warehouse_name': item.default_warehouse}, limit=1)[0].name
		item.insert()

def setup_warehouse():
	w = frappe.new_doc('Warehouse')
	w.warehouse_name = 'Supplier'
	w.insert()

def setup_currency_exchange():
	frappe.get_doc({
		'doctype': 'Currency Exchange',
		'from_currency': 'EUR',
		'to_currency': 'USD',
		'exchange_rate': 1.13
	}).insert()

	frappe.get_doc({
		'doctype': 'Currency Exchange',
		'from_currency': 'CNY',
		'to_currency': 'USD',
		'exchange_rate': 0.16
	}).insert()

def setup_product_bundle():
	frappe.get_doc({
		'doctype': 'Product Bundle',
		'new_item_code': 'Wind Mill A Series with Spare Bearing',
		'items': [
			{'item_code': 'Wind Mill A Series', 'qty': 1},
			{'item_code': 'Bearing Collar', 'qty': 1},
			{'item_code': 'Bearing Assembly', 'qty': 1},
		]
	}).insert()

def setup_user():
	frappe.db.sql('delete from tabUser where name not in ("Guest", "Administrator")')
	for u in json.loads(open(frappe.get_app_path('erpnext', 'demo', 'data', 'user.json')).read()):
		user = frappe.new_doc("User")
		user.update(u)
		user.flags.no_welcome_mail
		user.password = 'demo'
		user.insert()

def import_json(doctype, submit=False, values=None):
	frappe.flags.in_import = True
	data = json.loads(open(frappe.get_app_path('erpnext', 'demo', 'data',
		frappe.scrub(doctype) + '.json')).read())
	for d in data:
		doc = frappe.new_doc(doctype)
		doc.update(d)
		doc.insert()
		if submit:
			doc.submit()

	frappe.db.commit()

def setup_employee():
	frappe.db.set_value("HR Settings", None, "emp_created_by", "Naming Series")
	frappe.db.commit()

	import_json('Employee')

def setup_item_price():
	frappe.db.sql("delete from `tabItem Price`")

	standard_selling = {
		"Base Bearing Plate": 28,
		"Base Plate": 21,
		"Bearing Assembly": 300,
		"Bearing Block": 14,
		"Bearing Collar": 103.6,
		"Bearing Pipe": 63,
		"Blade Rib": 46.2,
		"Disc Collars": 42,
		"External Disc": 56,
		"Internal Disc": 70,
		"Shaft": 340,
		"Stand": 400,
		"Upper Bearing Plate": 300,
		"Wind Mill A Series": 320,
		"Wind Mill A Series with Spare Bearing": 750,
		"Wind MIll C Series": 400,
		"Wind Turbine": 400,
		"Wing Sheet": 30.8
	}

	standard_buying = {
		"Base Bearing Plate": 20,
		"Base Plate": 28,
		"Base Plate Un Painted": 16,
		"Bearing Block": 13,
		"Bearing Collar": 96.4,
		"Bearing Pipe": 55,
		"Blade Rib": 38,
		"Disc Collars": 34,
		"External Disc": 50,
		"Internal Disc": 60,
		"Shaft": 250,
		"Stand": 300,
		"Upper Bearing Plate": 200,
		"Wing Sheet": 25
	}

	for price_list in ("standard_buying", "standard_selling"):
		for item, rate in locals().get(price_list).iteritems():
			frappe.get_doc({
				"doctype": "Item Price",
				"price_list": price_list.replace("_", " ").title(),
				"item_code": item,
				"selling": 1 if price_list=="standard_selling" else 0,
				"buying": 1 if price_list=="standard_buying" else 0,
				"price_list_rate": rate,
				"currency": "USD"
			}).insert()

def setup_salary_structure():
	f = frappe.get_doc('Fiscal Year', frappe.defaults.get_global_default('fiscal_year'))

	for e in frappe.get_all('Employee', fields=['name', 'date_of_joining']):
		ss = frappe.new_doc('Salary Structure')
		ss.employee = e.name

		if not e.date_of_joining:
			continue

		ss.from_date = e.date_of_joining if (e.date_of_joining
			and e.date_of_joining > f.year_start_date) else f.year_start_date
		ss.to_date = f.year_end_date
		ss.append('earnings', {
			'salary_component': 'Basic',
			'amount': random.random() * 10000
		})
		ss.append('deductions', {
			'salary_component': 'Income Tax',
			'amount': random.random() * 1000
		})

		ss.insert()

def setup_account():
	frappe.flags.in_import = True
	data = json.loads(open(frappe.get_app_path('erpnext', 'demo', 'data',
		'account.json')).read())
	for d in data:
		doc = frappe.new_doc('Account')
		doc.update(d)
		doc.parent_account = frappe.db.get_value('Account', {'account_name': doc.parent_account})
		doc.insert()

def setup_user_roles():
	if not frappe.db.get_global('demo_hr_user'):
		user = frappe.get_doc('User', 'CharmaineGaudreau@example.com')
		user.add_roles('HR User', 'HR Manager', 'Accounts User')
		frappe.db.set_global('demo_hr_user', user.name)

	if not frappe.db.get_global('demo_sales_user_1'):
		user = frappe.get_doc('User', 'VakhitaRyzaev@example.com')
		user.add_roles('Sales User')
		frappe.db.set_global('demo_sales_user_1', user.name)

	if not frappe.db.get_global('demo_sales_user_2'):
		user = frappe.get_doc('User', 'GabrielleLoftus@example.com')
		user.add_roles('Sales User', 'Sales Manager', 'Accounts User')
		frappe.db.set_global('demo_sales_user_2', user.name)

	if not frappe.db.get_global('demo_purchase_user'):
		user = frappe.get_doc('User', 'MichalSobczak@example.com')
		user.add_roles('Purchase User', 'Purchase Manager', 'Accounts User', 'Stock User')
		frappe.db.set_global('demo_purchase_user', user.name)

	if not frappe.db.get_global('demo_manufacturing_user'):
		user = frappe.get_doc('User', 'NuranVerkleij@example.com')
		user.add_roles('Manufacturing User', 'Stock User', 'Purchase User', 'Accounts User')
		frappe.db.set_global('demo_manufacturing_user', user.name)

	if not frappe.db.get_global('demo_stock_user'):
		user = frappe.get_doc('User', 'HatsueKashiwagi@example.com')
		user.add_roles('Manufacturing User', 'Stock User', 'Purchase User', 'Accounts User')
		frappe.db.set_global('demo_stock_user', user.name)

	if not frappe.db.get_global('demo_accounts_user'):
		user = frappe.get_doc('User', 'LeonAbdulov@example.com')
		user.add_roles('Accounts User', 'Accounts Manager', 'Sales User', 'Purchase User')
		frappe.db.set_global('demo_accounts_user', user.name)

