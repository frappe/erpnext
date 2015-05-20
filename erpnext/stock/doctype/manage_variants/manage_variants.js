// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Manage Variants", {
	onload: function(frm) {
		var df = frappe.meta.get_docfield("Variant Attribute", "attribute_value");
		df.on_make = function(field) {
			field.$input.autocomplete({
				minLength: 0,
				minChars: 0,
				source: function(request, response) {
					frappe.call({
						method:"frappe.client.get_list",
						args:{
							doctype:"Variant Attribute",
							filters: [
								["parent","=", field.doc.attribute],
								["attribute_value", "like", request.term + "%"]
							],
							fields: ["attribute_value"]
						},
						callback: function(r) {
							response($.map(r.message, function(d) { return d.attribute_value; }));
						}
					});
				},
				select: function(event, ui) {
					field.$input.val(ui.item.value);
					field.$input.trigger("change");
				},
				focus: function( event, ui ) {
					if(ui.manage_variants.action) {
						return false;
					}
				},
			});
		}
	},

	refresh: function(frm) {
		frm.disable_save();
	}
	
});
