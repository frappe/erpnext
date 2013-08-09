# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes, os, datetime
import webnotes.utils
import random

webnotes.session = webnotes._dict({"user":"Administrator"})
from core.page.data_import_tool.data_import_tool import upload

company = "Wind Power LLC"
start_date = '2010-01-01'
runs_for = 100
prob = {
	"Quotation": { "make": 0.5, "qty": (1,3) },
	"Sales Order": { "make": 0.5, "qty": (1,2) }
}

def make():
	webnotes.connect()
	webnotes.print_messages = True
	webnotes.mute_emails = True

	# setup()
	simulate()
	
def setup():
	install()
	complete_setup()
	make_items()
	make_customers_suppliers_contacts()
	make_users_and_employees()
	# make_opening_stock()
	# make_opening_accounts()

def simulate():
	current_date = None
	for i in xrange(runs_for):
		print i
		if not current_date:
			current_date = webnotes.utils.getdate(start_date)
		else:
			current_date = webnotes.utils.add_days(current_date, 1)
			
		if current_date.weekday() in (5, 6):
			continue

		run_sales(current_date)
		run_purchase(current_date)
		run_manufacturing(current_date)
		
	webnotes.conn.commit()

def run_sales(current_date):
	if random.random() < prob["Quotation"]["make"]:
		for i in xrange(random.randrange(*prob["Quotation"]["qty"])):
			make_quotation(current_date)
			
	if random.random() < prob["Sales Order"]["make"]:
		for i in xrange(random.randrange(*prob["Sales Order"]["qty"])):
			make_sales_order(current_date)

def run_purchase(current_date):
	pass
	
def run_manufacturing(current_date):
	ppt = webnotes.bean("Production Planning Tool", "Production Planning Tool")
	ppt.doc.company = company
	ppt.doc.use_multi_level_bom = 1
	ppt.doc.purchase_request_for_warehouse = "Stores - WP"
	ppt.run_method("get_open_sales_orders")
	ppt.run_method("get_items_from_so")
	ppt.run_method("raise_production_order")
	ppt.run_method("raise_purchase_request")
	
	# submit production orders
	for pro in webnotes.conn.get_values("Production Order", {"docstatus": 0}):
		b = webnotes.bean("Production Order", pro[0])
		b.doc.wip_warehouse = "Work in Progress - WP"
		b.submit()
		
	# submit material requests
	for pro in webnotes.conn.get_values("Material Request", {"docstatus": 0}):
		b = webnotes.bean("Material Request", pro[0])
		b.submit()
	
def make_quotation(current_date):
	b = webnotes.bean([{
		"creation": current_date,
		"doctype": "Quotation",
		"quotation_to": "Customer",
		"customer": get_random("Customer"),
		"order_type": "Sales",
		"price_list_name": "Standard Selling",
		"transaction_date": current_date,
		"fiscal_year": "2010"
	}])
	
	add_random_children(b, {
		"doctype": "Quotation Item", 
		"parentfield": "quotation_details", 
	}, rows=3, randomize = {
		"qty": (1, 5),
		"item_code": ("Item", {"is_sales_item": "Yes"})
	}, unique="item_code")
	
	b.insert()
	b.submit()
	
def make_sales_order(current_date):
	q = get_random("Quotation", {"status": "Submitted"})
	from selling.doctype.quotation.quotation import make_sales_order
	so = webnotes.bean(make_sales_order(q))
	so.doc.transaction_date = current_date
	so.doc.delivery_date = webnotes.utils.add_days(current_date, 10)
	so.insert()
	so.submit()
	
def add_random_children(bean, template, rows, randomize, unique=None):
	for i in xrange(random.randrange(1, rows)):
		d = template.copy()
		for key, val in randomize.items():
			if isinstance(val[0], basestring):
				d[key] = get_random(*val)
			else:
				d[key] = random.randrange(*val)
		
		if unique:
			if not bean.doclist.get({"doctype": d["doctype"], unique:d[unique]}):
				bean.doclist.append(d)
		else:
			bean.doclist.append(d)

def get_random(doctype, filters=None):
	condition = []
	if filters:
		for key, val in filters.items():
			condition.append("%s='%s'" % (key, val))
	if condition:
		condition = " where " + " and ".join(condition)
	else:
		condition = ""
		
	out = webnotes.conn.sql("""select name from `tab%s` %s
		order by RAND() limit 0,1""" % (doctype, condition))[0][0]

	return out

def install():
	print "Creating Fresh Database..."
	from webnotes.install_lib.install import Installer
	inst = Installer('root')
	inst.import_from_db("demo", verbose = 1)

def complete_setup():
	print "Complete Setup..."
	webnotes.get_obj("Setup Control").setup_account({
		"first_name": "Test",
		"last_name": "User",
		"fy_start": "1st Jan",
		"industry": "Manufacturing",
		"company_name": company,
		"company_abbr": "WP",
		"currency": "USD",
		"timezone": "America/New York",
		"country": "United States"
	})

	import_data("Fiscal_Year")
	
def make_items():
	import_data(["Item", "Item_Price", "BOM"])
	
def make_customers_suppliers_contacts():
	import_data(["Customer", "Supplier", "Contact", "Address", "Lead"])

def make_users_and_employees():
	webnotes.conn.set_value("HR Settings", None, "emp_created_by", "Naming Series")
	webnotes.conn.commit()
	
	import_data(["Profile", "Employee", "Salary_Structure"])
	
def import_data(dt):
	if not isinstance(dt, (tuple, list)):
		dt = [dt]
	
	for doctype in dt:
		print "Importing", doctype.replace("_", " "), "..."
		webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", doctype+".csv")
		upload()

if __name__=="__main__":
	make()