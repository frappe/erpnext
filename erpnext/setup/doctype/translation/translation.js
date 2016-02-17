frappe.require("assets/erpnext/js/controllers/load_languages.js");

frappe.ui.form.on('Translation', {
	language: function(frm, cdt, cdn) {
		frm.cscript.update_language_code(frm)
	}
});

cur_frm.cscript.update_language_code = function(frm){
	var doc = frm.doc;
	frm.set_value('language_code', frappe.boot.lang_dict[doc.language])
}
