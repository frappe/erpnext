// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('company', 'default_letter_head', 'letter_head');


cur_frm.cscript.onload = function(doc, dt, dn){
	e_tbl = doc.earnings || [];
	d_tbl = doc.deductions || [];
	if (e_tbl.length == 0 && d_tbl.length == 0)
		return function(r, rt) { refresh_many(['earnings', 'deductions']);};
}

frappe.ui.form.on('Salary Structure', {
	onload: function(frm) {
		frm.set_query("salary_component", "earnings", function() {
			return {
				filters: {
					type: "earning"
				}
			}
		})
		frm.set_query("salary_component", "deductions", function() {
			return {
				filters: {
					type: "deduction"
				}
			}
		})
	},
	
	refresh: function(frm) {
		frm.trigger("toggle_fields")
		frm.fields_dict['earnings'].grid.set_column_disp("default_amount", false);
		frm.fields_dict['deductions'].grid.set_column_disp("default_amount", false);
		
		frm.add_custom_button(__("Preview Salary Slip"),
			function() { frm.trigger('preview_salary_slip'); }, "icon-sitemap", "btn-default");
		
	},	

	salary_slip_based_on_timesheet: function(frm) {
		frm.trigger("toggle_fields")
	},
	
	preview_salary_slip: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __("Preview Salary Slip"),
			fields: [
				{"fieldname":"employee", "fieldtype":"Select", "label":__("Employee"),
				options: $.map(frm.doc.employees, function(d) { return d.employee }), reqd: 1, label:"Employee"},
				{fieldname:"fetch", "label":__("Show Salary Slip"), "fieldtype":"Button"}
			]
		});
		d.get_input("fetch").on("click", function() {
			var values = d.get_values();
			if(!values) return;
			frm.doc.salary_slip_based_on_timesheet?print_format="Salary Slip based on Timesheet":print_format="Salary Slip Standard";
				
			frappe.call({
				method: "erpnext.hr.doctype.salary_structure.salary_structure.make_salary_slip",
				args: {
					source_name: frm.doc.name,
					employee: values.employee,
					as_print: 1,
					print_format: print_format
				},
				callback: function(r) {
					var new_window = window.open();
					new_window.document.write(r.message);
					// frappe.msgprint(r.message);
				}
			});
		});
		d.show();
	},
	
	toggle_fields: function(frm) {
		frm.toggle_display(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
		frm.toggle_reqd(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
	}
})


cur_frm.cscript.amount = function(doc, cdt, cdn){
	calculate_totals(doc, cdt, cdn);
}

var calculate_totals = function(doc) {
	var tbl1 = doc.earnings || [];
	var tbl2 = doc.deductions || [];

	var total_earn = 0; var total_ded = 0;
	for(var i = 0; i < tbl1.length; i++){
		total_earn += flt(tbl1[i].amount);
	}
	for(var j = 0; j < tbl2.length; j++){
		total_ded += flt(tbl2[j].amount);
	}
	doc.total_earning = total_earn;
	doc.total_deduction = total_ded;
	doc.net_pay = 0.0
	if(doc.salary_slip_based_on_timesheet == 0){
		doc.net_pay = flt(total_earn) - flt(total_ded);
	}

	refresh_many(['total_earning', 'total_deduction', 'net_pay']);
}

cur_frm.cscript.validate = function(doc, cdt, cdn) {
	calculate_totals(doc);
	if(doc.employee && doc.is_active == "Yes") frappe.model.clear_doc("Employee", doc.employee);
}


frappe.ui.form.on('Salary Detail', {
	amount: function(frm) {
		calculate_totals(frm.doc);
	},
	
	earnings_remove: function(frm) {
		calculate_totals(frm.doc);
	}, 
	
	deductions_remove: function(frm) {
		calculate_totals(frm.doc);
	}
})

frappe.ui.form.on('Salary Structure Employee', {
	onload: function(frm) {
		frm.set_query("employee","employees", function(doc,cdt,cdn) {
			return{ query: "erpnext.controllers.queries.employee_query" }
		})
	}
});
