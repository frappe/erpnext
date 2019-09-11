from __future__ import unicode_literals
from frappe import _

doctype_rule_map = {
	'Item': {
		'points': 5,
		'for_doc_event': 'New'
	},
	'Customer': {
		'points': 5,
		'for_doc_event': 'New'
	},
	'Supplier': {
		'points': 5,
		'for_doc_event': 'New'
	},
	'Lead': {
		'points': 2,
		'for_doc_event': 'New'
	},
	'Sales Order': {
		'points': 10,
		'for_doc_event': 'Submit',
		'rule_name': __('On Sales Order Submission')
	},
	'Purchase Order': {
		'points': 10,
		'for_doc_event': 'Submit',
		'rule_name': __('On Purchase Order Submission')
	},
	'Task': {
		'points': 5,
		'condition': 'doc.status == "Completed"',
		'rule_name': __('On Task Completion'),
		'user_field': 'completed_by'
	}
}

def get_default_energy_point_rules():
	return [{
		'doctype': 'Energy Point Rule',
		'reference_doctype': doctype,
		'for_doc_event': rule.get('for_doc_event') or 'Custom',
		'condition': rule.get('condition')
		'rule_name': rule.get('rule_name') or __('On {0} Creation').format(doctype),
		'points': rule.get('points'),
		'user_field': rule.get('user_field') or 'Owner'
	} for doctype, rule in doctype_rule_map.iteritems()]

