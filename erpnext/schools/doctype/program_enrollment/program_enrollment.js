// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt

cur_frm.add_fetch('fee_structure', 'total_amount', 'amount');

frappe.ui.form.on("Program Enrollment", {
	program: function(frm) {
		if (frm.doc.program) {
			frappe.call({
				method: "erpnext.schools.api.get_fee_schedule",
				args: {
					"program": frm.doc.program,
					"student_category": frm.doc.student_category
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("fees" ,r.message);
					}
				}
			});
		}
	},
	
	student_category: function() {
		frappe.ui.form.trigger("Program Enrollment", "program");
	},
	
	onload: function(frm, cdt, cdn){
		cur_frm.set_query("academic_term", "fees", function(){
			return{
				"filters":{
					"academic_year": (frm.doc.academic_year)
				}
			};
		});
				
		cur_frm.fields_dict['fees'].grid.get_field('fee_structure').get_query = function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {'academic_term': d.academic_term}
			}
		};
		
	}
});
