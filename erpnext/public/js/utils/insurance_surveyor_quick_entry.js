frappe.provide('frappe.ui.form');

frappe.ui.form.InsuranceSurveyorQuickEntryForm = class InsuranceSurveyorQuickEntryForm extends frappe.ui.form.QuickEntryForm {
	init(doctype, after_insert) {
		super.init(doctype, after_insert);
	}

	render_dialog() {
		super.render_dialog();
		if (this.dialog.get_field("insurance_company")) {
			this.dialog.get_field("insurance_company").get_query = function () {
				return {
					query: "erpnext.controllers.queries.customer_query",
					filters: {'is_insurance_company': 1}
				}
			}
		}
	}
};