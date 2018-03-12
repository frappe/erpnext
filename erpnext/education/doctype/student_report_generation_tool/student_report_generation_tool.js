// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student Report Generation Tool', {
	onload: function(frm) {
		frm.set_query("academic_term",function(){
			return{
				"filters":{
					"academic_year": frm.doc.academic_year
				}
			};
		});
		frm.set_query("assessment_group", function() {
			return{
				filters: {
					"is_group": 1
				}
			};
		});
	},

	refresh: function(frm) {
		frm.disable_save();
		frm.page.clear_indicator();
		frm.fields_dict.preview_report_card.$input.addClass("btn-primary");
	},

	preview_report_card: function(frm) {
		let url = "/api/method/erpnext.education.doctype.student_report_generation_tool.student_report_generation_tool.preview_report_card";
		open_url_post(url, frm.doc);
	}
});
