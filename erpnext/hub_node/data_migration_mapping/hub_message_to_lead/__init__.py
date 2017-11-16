import frappe, json

def pre_process(doc):
	return json.loads(doc['data'])

def post_process(remote_doc=None, local_doc=None, **kwargs):
	if not local_doc:
		return

	hub_message = remote_doc
	# update hub message on hub
	hub_connector = frappe.get_doc('Data Migration Connector', 'Hub Connector')
	connection = hub_connector.get_connection()
	connection.update('Hub Message', dict(
		status='Synced'
	), hub_message['name'])

	# make opportunity after lead is created
	lead = local_doc
	opportunity = frappe.get_doc({
		'doctype': 'Opportunity',
		'naming_series': 'OPTY-',
		'opportunity_type': 'Hub',
		'enquiry_from': 'Lead',
		'status': 'Open',
		'lead': lead.name,
		'company': lead.company,
		'transaction_date': frappe.utils.today()
	}).insert()
