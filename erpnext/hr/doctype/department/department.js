// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Department', {
	refresh: function(frm) {

	}
});

cur_frm.cscript.custom_line_manager =function(doc,cdt,cdn){
	// frappe.call({
	// 	doc: doc,
	// 	args:{"emp":doc.line_manager,"role":"Line Manager"},
	// 	method: "add_remove_roles",
	// 	callback: function(r) {
	// 		console.log(r.message);
	// 	}
	// });
};
cur_frm.cscript.custom_department_manager =function(doc,cdt,cdn){
	// frappe.call({
	// 	doc: doc,
	// 	args:{"emp":doc.department_manager,"role":"Department Manager"},
	// 	method: "add_remove_roles",
	// 	callback: function(r) {
	// 		console.log(r.message);
	// 		cur_frm.refresh();
	// 	}
	// });
};
cur_frm.cscript.custom_vice_presedint =function(doc,cdt,cdn){
	// frappe.call({
	// 	doc: doc,
	// 	args:{"emp":doc.vice_presedint,"role":"Vice Presedint"},
	// 	method: "add_remove_roles",
	// 	callback: function(r) {
	// 		console.log(r.message);
	// 	}
	// });
};
cur_frm.cscript.custom_regional_director =function(doc,cdt,cdn){
	// frappe.call({
	// 	doc: doc,
	// 	args:{"emp":doc.regional_director,"role":"Regional Director"},
	// 	method: "add_remove_roles",
	// 	callback: function(r) {
	// 		console.log(r.message);
	// 	}
	// });
};
