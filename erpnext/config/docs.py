source_link = "https://github.com/frappe/erpnext"
docs_base_url = "https://frappe.github.io/erpnext"
headline = "Learn ERPNext Inside Out"
sub_heading = "Find detailed explanation for all ERPNext features"
long_description = """ERPNext is a fully featured ERP system designed for Small and Medium Sized
business. ERPNext covers a wide range of features including Accounting, CRM,
Inventory management, Selling, Purchasing, Manufacturing, Projects, HR &
Payroll, Website, E-Commerce and much more.

ERPNext is based on the Frappe Framework is highly customizable and extendable.
You can create Custom Form, Fields, Scripts and can also create your own Apps
to extend ERPNext functionality.

ERPNext is Open Source under the GNU General Public Licence v3 and has been
listed as one of the Best Open Source Softwares in the world by my online
blogs."""

def get_context(context):
	context.top_bar_items = [
		{"label": "Contents", "url": context.docs_base_url + "/contents.html", "right": 1},
		{"label": "User Guide", "url": context.docs_base_url + "/user/guides", "right": 1},
		{"label": "Videos", "url": context.docs_base_url + "/user/videos", "right": 1},
		{"label": "Developer Docs", "url": context.docs_base_url + "/current", "right": 1}
	]
