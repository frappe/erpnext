// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Manage Variants", {
	onload: function(frm) {
		var df = frappe.meta.get_docfield("Variant Attribute", "attribute_value", "Manage Variants");
		df.on_make = function(field) {
			$(field.input_area).addClass("ui-front");
			field.$input.autocomplete({
				minLength: 0,
				minChars: 0,
				source: function(request, response) {
					frappe.call({
						method:"frappe.client.get_list",
						args:{
							doctype:"Item Attribute Value",
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
				}
			});
		}
	},

	refresh: function(frm) {
		frm.disable_save();
		frm.page.set_primary_action(__("Create Variants"), function() {
			frappe.call({
				method: "create_variants",
				doc:frm.doc
			})
		});
	},
	
	onload_post_render: function(frm) {
		frm.get_field("variants").grid.cannot_add_rows = true;
	},

	item_code:function(frm) {
		return frappe.call({
			method: "get_item_details",
			doc:frm.doc,
			callback: function(r) {
				refresh_field('attributes');
				refresh_field('variants');
			}
		})
	}
});
