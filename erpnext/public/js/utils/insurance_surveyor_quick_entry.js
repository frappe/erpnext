frappe.provide('frappe.ui.form');

frappe.ui.form.InsuranceSurveyorQuickEntryForm = frappe.ui.form.QuickEntryForm.extend({
	init: function(doctype, after_insert) {
		this._super(doctype, after_insert);
	},

	render_dialog: function() {
		this._super();
		this.dialog.get_field("insurance_company").get_query = function () {
			return {
				filters: {
					'is_insurance_company': 1
				}
			}
		}
	},
});