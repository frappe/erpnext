source_link = "https://github.com/frappe/erpnext"
docs_base_url = "https://frappe.github.io/erpnext"
headline = "Learn ERPNext Inside Out"
sub_heading = "Find detailed explanation for all ERPNext features"
long_description = """
ERPNext helps you to manage all your business information in one application and use it to manage operations and take decisions based on data.

Among other things, ERPNext will help you to:

- Track all Invoices and Payments.
- Know what quantity of which product is available in stock.
- Identify open customer queries.
- Manage payroll.
- Assign tasks and follow up on them.
- Maintain a database of all your customers, suppliers and their contacts.
- Prepare quotes.
- Get reminders on maintenance schedules.
- Publish your website.

And a lot lot lot more."""

def get_context(context):
	context.top_bar_items = [
		{"label": "Contents", "url": context.docs_base_url + "/contents.html", "right": 1},
		{"label": "User Guide", "url": context.docs_base_url + "/user/guides", "right": 1},
		{"label": "Videos", "url": context.docs_base_url + "/user/videos", "right": 1},
		{"label": "Developer Docs", "url": context.docs_base_url + "/current", "right": 1}
	]
