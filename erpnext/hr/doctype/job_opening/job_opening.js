// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Opening', {
	onload: function(frm) {
		frm.set_query("department", function() {
			return {
				"filters": {
					"company": frm.doc.company,
				}
			};
		});
	},
	designation: function(frm) {
		if(frm.doc.designation && frm.doc.company){
			frappe.call({
				"method": "erpnext.hr.doctype.staffing_plan.staffing_plan.get_active_staffing_plan_details",
				args: {
					company: frm.doc.company,
					designation: frm.doc.designation,
					date: frappe.datetime.now_date() // ToDo - Date in Job Opening?
				},
				callback: function (data) {
					if(data.message){
						frm.set_value('staffing_plan', data.message[0].name);
						frm.set_value('planned_vacancies', data.message[0].vacancies);
					} else {
						frm.set_value('staffing_plan', "");
						frm.set_value('planned_vacancies', 0);
						frappe.show_alert({
							indicator: 'orange',
							message: __('No Staffing Plans found for this Designation')
						});
					}
				}
			});
		}
		else{
			frm.set_value('staffing_plan', "");
			frm.set_value('planned_vacancies', 0);
		}
	},
	company: function(frm) {
		frm.set_value('designation', "");
	}
});
