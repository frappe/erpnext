import frappe
from frappe.email import sendmail_to_system_managers

def execute():
	frappe.reload_doc('regional', 'doctype', 'gst_hsn_code')

	for report_name in ('GST Sales Register', 'GST Purchase Register',
		'GST Itemised Sales Register', 'GST Itemised Purchase Register'):

		frappe.reload_doc('regional', 'report', frappe.scrub(report_name))

	if frappe.db.get_single_value('System Settings', 'country')=='India':
		from erpnext.regional.india.setup import setup
		setup()
		send_gst_update_email()

def send_gst_update_email():
	message = """Hello,

<p>ERPNext is now GST Ready.</p>

<p>To start making GST Invoices from 1st of July, you just need to create new Tax Accounts, Templates and update your Customer's and Supplier's GST Numbers.</p>

<p>Please refer {gst_document_link} to know more about how to setup and implement GST in ERPNext.</p>

<p>Please contact us at support@erpnext.com, if you have any questions.</p>

<p>Thanks,</p>
ERPNext Team.
	""".format(gst_document_link="<a href='http://frappe.github.io/erpnext/user/manual/en/regional/india/'> ERPNext GST Document </a>")

	sendmail_to_system_managers("[Important] ERPNext GST updates", message)

