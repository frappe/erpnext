// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bar Code Generate', {
	refresh: function(frm) {

	}
});

erpnextBarCodeGenerateControler = frappe.ui.form.Controller.extend({
	onload:function (doc,doctype,docname) {
		local = locals[doctype][docname]
		console.log(local)
        this.frm.set_query("operation", function() {
			frappe.model.validate_missing(doc, "production_order");
	        return {
	            filters: {
	                // "reference": doc.style,
	            }
	        };
	    });
	}
});

cur_frm.cscript = new erpnextBarCodeGenerateControler({frm:cur_frm})