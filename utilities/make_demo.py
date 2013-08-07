# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes, os, datetime
import webnotes.utils
import random

webnotes.session = webnotes._dict({"user":"Administrator"})
from core.page.data_import_tool.data_import_tool import upload

start_date = '2010-01-01'
runs_for = 100
prob = {
	"Quotation": 0.5
}

def make():
	webnotes.connect()
	webnotes.print_messages = True
	webnotes.mute_emails = True

	# setup()
	# simulate()
	make_quotation("2010-01-01")
	webnotes.conn.commit()
	
def setup():
	install()
	complete_setup()
	make_items()
	make_customers_suppliers_contacts()
	make_users_and_employees()
	# make_bom()
	# make_opening_stock()
	# make_opening_accounts()

def simulate():
	current_date = None
	for i in xrange(runs_for):
		if not current_date:
			current_date = webnotes.utils.getdate(start_date)
		else:
			current_date = webnotes.utils.add_days(current_date, 1)
			
		if current_date.weekday() in (5, 6):
			continue

		run_sales(current_date)

	webnotes.conn.commit()
		

def run_sales(current_date):
	if random.random() < prob["Quotation"]:
		make_quotation(current_date)
		
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
	print b.doc.name
	
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
		"company_name": "Wind Power LLC",
		"company_abbr": "WP",
		"currency": "USD",
		"timezone": "America/New York",
		"country": "United States"
	})

	print "Importing Fiscal Years..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Fiscal_Year.csv")
	upload()

	
def make_items():
	print "Importing Items..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Item.csv")
	upload()
	print "Importing Item Prices..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Item_Price.csv")
	upload()
	
def make_customers_suppliers_contacts():
	print "Importing Customers..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Customer.csv")
	upload()
	print "Importing Suppliers..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Supplier.csv")
	upload()
	print "Importing Contacts..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Contact.csv")
	upload()
	print "Importing Address..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Address.csv")
	upload()
	print "Importing Lead..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Lead.csv")
	upload()

def make_users_and_employees():
	print "Importing Profile..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Profile.csv")
	upload()
	webnotes.conn.set_value("HR Settings", None, "emp_created_by", "Naming Series")
	webnotes.conn.commit()
	
	print "Importing Employee..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Employee.csv")
	upload()

	print "Importing Salary Structure..."
	webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", "Salary_Structure.csv")
	upload()

if __name__=="__main__":
	make()