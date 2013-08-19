---
{
	"_label": "Web Service API"
}
---
All communication with the ERPNext server happens via web services using HTTP requests and passing data via JSON (Javascript Object Notation). Using web requests you can insert, update, query, run public triggers etc. The basic scheme is as follows:

1. All API calls are to me made to `server.py` on your public folder of your erpnext account. For hosted users, it is (yourdomain.erpnext.com).
1. The `cmd` parameter points to the python function to be executed.
1. Authentication is managed using cookies.

### Authentication

Authentication is done via the login method:

	GET server.py?cmd=login&usr=[username]&password=[password]

The login method returns a session id `sid` cookie in the header and a status in the
body of the request. The `sid` cookie must be sent for each subsequent request.
	
Example:

	$ curl -I http://localhost/webnotes/erpnext/public/server.py?cmd=login\&usr=Administrator\&pwd=admin
	HTTP/1.1 200 OK
	Date: Tue, 23 Jul 2013 05:29:24 GMT
	Server: Apache/2.2.22 (Unix) DAV/2 mod_ssl/2.2.22 OpenSSL/0.9.8r
	Set-Cookie: country=None
	Set-Cookie: sid=d0ce00d49c24869984960607a2467b50ff59b0024741922db4b23818; expires=Fri, 26 Jul 2013 10:59:25
	Content-Length: 32
	Content-Type: text/html; charset: utf-8
		
	{"message":"Logged In","exc":""}
	
	$ curl http://localhost/webnotes/erpnext/public/server.py?cmd=webnotes.client.get\&doctype=Profile\&name=Administrator -b sid=d0ce00d49c24869984960607a2467b50ff59b0024741922db4b23818
	
	{
		"message":[
			{
				"user_image":null,
				"last_name":"User",
				"last_ip":"::1",
				..
				..
### Python Remote Client

You can use the `webclient.py` module as an example of how to access data using the webservice API

- [Code](https://github.com/webnotes/wnframework/blob/master/webnotes/utils/webclient.py)
- [Docs](http://erpnext.org/docs.dev.framework.server.webnotes.utils.webclient.html)

### Passing and Receiving Documents (`doclist`)

To insert or update documents in ERPNext you have to pass them as a JSON Object. The structure of a Document is a list of plain objects (called `doclist`). The `doclist`
contains the the parent document and any child documents (if they are present).

Example:

	[{
		"doctype": "Parent"
		"key1": "value1"
		..
	},{
		"doctype": "Child",
		"parenttype": "Parent",
		"parentfield": "children",
		"key1", "value1",
		..
	}]

### webnotes.client

`webnotes.client` is the easiest way to interact with the ERPNext Server. It contains
a bunch of server-side public methods that can be used by any client.

- [Code](https://github.com/webnotes/wnframework/blob/master/webnotes/client.py)
- [Docs](http://erpnext.org/docs.dev.framework.server.webnotes.client.html)

### Example

Here is an example how you can use the webclient module to insert a new Sales Invoice
in ERPNext.

	from webclient import *
 
	server = "http://myaccount.erpnext.com/server.py"
	user = "your user name"
	password = "your password"
 
	login()
 
	customer = get_doc("Customer", customer_name)
 
	# make customer if required
	if not customer:
	  	response = insert([{
			"doctype":"Customer",
			"customer_name": customer_name,
			"customer_type": "Company",
			"customer_group": "Standard Group",
			"territory": "Default",
			"customer_details": "some unique info",
			"company": "Alpha"
		}])
    
	# make invoice
	resonse = insert([
	  	# main
	 	{
	  		"naming_series": "_T-Sales Invoice-",
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"debit_to": "_Test Customer - _TC",
			"customer": "_Test Customer",
			"customer_name": "_Test Customer",
			"doctype": "Sales Invoice", 
			"due_date": "2013-01-23", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"grand_total": 561.8, 
			"grand_total_export": 561.8, 
			"net_total": 500.0, 
			"plc_conversion_rate": 1.0, 
			"posting_date": "2013-01-23", 
			"price_list_currency": "INR", 
			"selling_price_list": "_Test Price List", 
			"territory": "_Test Territory"
		},
 
		# items 
		{
			"amount": 500.0, 
			"basic_rate": 500.0, 
			"description": "138-CMS Shoe", 
			"doctype": "Sales Invoice Item", 
			"export_amount": 500.0, 
			"export_rate": 500.0, 
			"income_account": "Sales - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"item_name": "138-CMS Shoe", 
			"parentfield": "entries",
			"qty": 1.0
		}, 
 
		# taxes
		{
			"account_head": "_Test Account VAT - _TC", 
			"charge_type": "On Net Total", 
			"description": "VAT", 
			"doctype": "Sales Taxes and Charges", 
			"parentfield": "other_charges",
			"tax_amount": 30.0,
		}, 
		{
			"account_head": "_Test Account Service Tax - _TC", 
			"charge_type": "On Net Total", 
			"description": "Service Tax", 
			"doctype": "Sales Taxes and Charges", 
			"parentfield": "other_charges",
			"tax_amount": 31.8,
		},
  
		# sales team
		{
			"parentfield": "sales_team",
			"doctype": "Sales Team",
			"sales_person": "_Test Sales Person 1",
			"allocated_percentage": 65.5,
		},
		{
			"parentfield": "sales_team",
			"doctype": "Sales Team",
			"sales_person": "_Test Sales Person 2",
			"allocated_percentage": 34.5,
		},
	)]


