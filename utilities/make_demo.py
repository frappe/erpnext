import webnotes, os
webnotes.session = webnotes._dict({"user":"Administrator"})
from core.page.data_import_tool.data_import_tool import upload

def make():
	webnotes.connect()
	webnotes.print_messages = True
	webnotes.mute_emails = True
	install()
	complete_setup()
	make_items()
	make_customers_suppliers_contacts()
	# make_bom()
	# make_opening_stock()
	# make_opening_accounts()
	
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
		"currency": "INR",
		"timezone": "America/New York",
		"country": "United States"
	})
	
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


if __name__=="__main__":
	make()