// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bar Code Generate', {
	refresh: function(frm) {
		frm.disable_save();
	}
});

erpnextBarCodeGenerateControler = frappe.ui.form.Controller.extend({
	onload:function (doc,doctype,docname) {
        this.frm.set_query("operation", function() {
			frappe.model.validate_missing(doc, "production_order");
	        return {
	        	filters:{
						parent:doc.production_order
					},
				searchfield:'operation'
			}
	    });
		this.frm.add_fetch('operation', 'completed_qty', 'bar_code_quantity');
	},
	operation: function(doc){
		set_available_quantity(doc);
		set_total_bar_code(doc);
	},
	bar_code_quantity: function (doc) {
		set_available_quantity(doc);
		set_total_bar_code(doc);
	},
	per_bar_code_quantity: function (doc) {
		set_total_bar_code(doc);
	},
    total_bar_code: function (doc) {
        set_per_bar_code(doc);
    }

});

cur_frm.cscript = new erpnextBarCodeGenerateControler({frm:cur_frm})

function set_available_quantity(doc) {
	doc.available_quantity = doc.total_oder_quantity - doc.bar_code_quantity;
	refresh_field('available_quantity')
}

function set_total_bar_code(doc){
	doc.total_bar_code = parseInt(doc.available_quantity / doc.per_bar_code_quantity);
	refresh_field('total_bar_code')
}

function set_per_bar_code(doc){
	doc.per_bar_code_quantity = parseInt(doc.available_quantity / doc.total_bar_code);
	refresh_field('per_bar_code_quantity')
}

