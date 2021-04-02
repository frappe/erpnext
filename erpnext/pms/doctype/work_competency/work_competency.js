// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Competency', {
	// refresh: function(frm) {

	// }
	competency: function(frm){
		get_employee_category(frm)
	},
	apply_to_all: function(frm){
		apply_to_all(frm)
	}
});

frappe.ui.form.on('Work Competency Item',{
	//to avoid deletion of child table items
	employee_category_item_remove(frm,cdt,cdn){
		get_employee_category(frm)
	}
})

function get_employee_category(frm){
		return frappe.call({
			method:'get_employee_category',
			doc:frm.doc,
			callback:function(){
				frm.refresh_field('employee_category_item');
				frm.refresh_field()
			}
	})
}
function apply_to_all(frm){
	var items = frm.doc.employee_category_item
	if (frm.doc.apply_to_all){
		items.map(function(rows){
			rows.applicable = 1
		})
	}else{
		items.map(function(rows){
			rows.applicable = 0
		})
	}
	refresh_field('employee_category_item')
}
