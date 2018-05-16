// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Benefit Application', {
	setup: function(frm) {
		frm.set_query("earning_component", "employee_benefits", function() {
			return {
				filters: {
					type: "Earning",
					is_flexible_benefit: true,
					disabled: false
				}
			};
		});
	},
	employee: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "get_max_benefits",
			callback: function (data) {
				if(!data.exc){
					if(data.message){
						frm.set_value("max_benefits", data.message);
					}
				}
			}
		});
	}
});

frappe.ui.form.on("Employee Benefit Application Detail",{
	amount:  function(frm, cdt, cdn) {
		calculate_all(frm.doc, cdt, cdn);
	}
});

var calculate_all = function(doc, dt, dn) {
	var tbl = doc.employee_benefits || [];
	var pro_rata_dispensed_amount = 0;
	var total_amount = 0;
	for(var i = 0; i < tbl.length; i++){
		if(cint(tbl[i].amount) > 0) {
			total_amount += flt(tbl[i].amount);
		}
		if(tbl[i].is_pro_rata_applicable == 1){
			pro_rata_dispensed_amount += flt(tbl[i].amount)
		}
	}
	doc.total_amount = total_amount;
	doc.remainig_benefits = doc.max_benefits - total_amount;
	doc.pro_rata_dispensed_amount = pro_rata_dispensed_amount;
	refresh_many(['pro_rata_dispensed_amount', 'total_amount','remainig_benefits']);
};
