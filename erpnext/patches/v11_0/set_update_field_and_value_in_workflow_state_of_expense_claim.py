import frappe
from frappe.model.workflow import get_workflow_name

def execute():
	active_workflow = get_workflow_name('Expense Claim')
	workflow_states = frappe.get_all('Workflow Document State',
		filters=[['parent', '=', active_workflow]],
		fields=['*'])

	for state in workflow_states:
		if state.update_field: return
		frappe.set_value('Workflow Document State', state.name, 'update_field', 'approval_status')
		frappe.set_value('Workflow Document State', state.name, 'update_value', state.state)

	frappe.db.commit()