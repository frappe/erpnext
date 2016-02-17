frappe.provide("erpnext")

cur_frm.cscript.before_load = function(doc, dt, dn, callback) {
	var update_language_select = function(user_language) {
		cur_frm.set_df_property("language", "options", frappe.languages || ["", "English"]);
		callback && callback();
	}

	if(!frappe.languages) {
		frappe.languages = frappe.boot.languages;
		update_language_select();
	} else {
		update_language_select();
	}
}
