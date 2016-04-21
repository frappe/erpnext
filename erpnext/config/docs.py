source_link = "https://github.com/frappe/erpnext"
docs_base_url = "https://frappe.github.io/erpnext"
headline = "ERPNext Documentation"
sub_heading = "Detailed explanation for all ERPNext features and developer API"
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

docs_version = "6.x.x"
splash_light_background = True

def get_context(context):
	context.brand_html = "ERPNext"
	context.app.splash_light_background = True
	context.top_bar_items = [
		{"label": "User Manual", "url": context.docs_base_url + "/user/manual", "right": 1},
		{"label": "Videos", "url": context.docs_base_url + "/user/videos", "right": 1},
		{"label": "API Documentation", "url": context.docs_base_url + "/current", "right": 1}
	]
