// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Alternative', {
	refresh: function(frm) {

	}
});

// Filters Alternatives Items item fields
// List all Items except current parent Item and already selected in child tables
// Can not select as Alternative Item the "self" or "this" item_code
cur_frm.fields_dict['alt_items'].grid.get_field('item').get_query = function(doc, cdt, cdn) {
	 var d = locals[cdt][cdn];
	 var allready_alt_items = []
	 if (cur_frm.doc.alt_items) {
		var current_alt_items = cur_frm.doc.alt_items
		for (var i = 0; i < current_alt_items.length; i++) {
			if (current_alt_items[i].item) {
				allready_alt_items.push(current_alt_items[i].item)
			}
		}
	 }
     return {
        filters: [
			['Item', 'item_code', '!=', cur_frm.doc.item],
			['Item', 'item_code', 'not in', allready_alt_items]
		]
    }
};

// Filter UOMs Detail based on row Alternative Item selection
cur_frm.fields_dict['alt_items'].grid.get_field('uom').get_query = function(doc, cdt, cdn) {
	 var d = locals[cdt][cdn];
     return {
        filters: [
			['UOM Conversion Detail', 'parent', '=', d.item],
		]
    }
};


cur_frm.validate_row = function(frm, cdt, cdn){
	// Basic on the fly child table validation. This is not set on "validate"
	// trigger as improves UI experience in a complex concept of Alternative Items.
	// End User must be carefull row by row data entry and not as a whole Doctype.

	var row = frappe.get_doc(cdt, cdn) // row doctype
	var current_idx = row.idx // child table idx : current_idx - 1

	// Row grid data are set
	if (row.item && row.uom && row.type) {
		// Check if selected item is already selected
		// This is an insanity check
		 if (row.type == __('One-Way')) {
			 // check the other direction
			 frappe.call({
				 method: 'erpnext.stock.doctype.item_alternative.item_alternative.check_one_way',
				 freeze: true,
				 freeze_message: __("Checking Relation..."),
				 args: {
					  cur_alt_item: row.item,
					  parent_item: frm.doc.item
				 },
				 callback: function(r){
					 if (r.message) {
						 // Throw expection in client side and remove it from child table
						 // This ensures on the fly validation
						 if (r.message == 'Remove') {
							 frm.doc.alt_items.splice(current_idx-1, 1)
					 		 frm.refresh()
						 	 frappe.throw(__("Invalid Alternative Item setup: "+ row.item + " with One-Way was already Two-Way connection with " + frm.doc.item))
						 }

					 }
				 }
			 })
		 }

		 if (row.type == __('Two-Way')) {
			 // load cache data from server side __onload
			 // self.Item UOMs details.
			 var uoms_details = cur_frm.doc.__onload.self_uoms
			 // check the other direction
			 // Prompt dialog for user to select the "self" UOM
			 // This improves UI as currently we are limited in 5 columns
			 // grid view.
			var d = new frappe.ui.Dialog({
				'title': __("UOMs - Two-Way Relation Setup"),
			    'fields': [
			        {'fieldname': 'parent_uom',
					 'fieldtype': 'Link',
					 'options': "UOM Conversion Detail",
				 	 'label': "Choice from current item,  " + cur_frm.doc.item + ", UOMs",
					 get_query: function() {
						return {filters: [['UOM Conversion Detail', 'parent', '=', cur_frm.doc.item],]}
				 	 }
				 	},
			    ],
				primary_action_label: __("Select"),
			    primary_action: function(){
					// Update child table fields based on user selection.
					row.parent_uom = d.get_values().parent_uom
					var uomdetail = uoms_details.find(function (obj) { return obj.name === row.parent_uom; });
					row.parent_uom_display = uomdetail.uom + " ~ " + uomdetail.conversion_factor
					frm.refresh()
					frappe.call({
						method: 'erpnext.stock.doctype.item_alternative.item_alternative.check_two_way',
						freeze: true,
						freeze_message: __("Checking Relation..."),
						args: {
							 cur_alt_item: row.item,
							 cur_item_uom: row.uom,
							 parent_item: frm.doc.item,
							 parent_uom: row.parent_uom
						}
					})
			        d.hide();
			    }
			});
			d.no_cancel()
			d.show();
		 }
	}
}

frappe.ui.form.on('Alternative List', {
	before_alt_items_remove: function(frm, cdt, cdn) {
		var deleted_row = frappe.get_doc(cdt, cdn);
		if (deleted_row.type == __('Two-Way')) {
			frappe.call({
				method: 'erpnext.stock.doctype.item_alternative.item_alternative.delete_two_way',
				args: {
					deleted_item: deleted_row.item,
					parent_item: cur_frm.doc.item
				}
			})
		}
	},
	item: function(frm, cdt, cdn){
		var row = frappe.get_doc(cdt, cdn)
		frappe.call({
			method: 'frappe.client.get',
			freeze: true,
			freeze_message: __("Fetching Item information"),
			args: {
				doctype: 'Item',
				name: row.item
			},
			callback: function(r){
				if (r.message) {
					row.item_name = r.message.item_name
					frm.refresh()
					cur_frm.validate_row(frm, cdt, cdn)
				}

			}
		})
	},
	uom: function(frm, cdt, cdn){
		var row = frappe.get_doc(cdt, cdn)
		frappe.call({
			method: 'frappe.client.get',
			freeze: true,
			freeze_message: __("Fetching UOM Information"),
			args: {
				doctype: 'UOM Conversion Detail',
				name: row.uom
			},
			callback: function(r){
				if (r.message) {
					row.uom_display = r.message.uom + " ~ " + r.message.conversion_factor
					frm.refresh()
					cur_frm.validate_row(frm, cdt, cdn)
				}
			}
		})
	},
	type: function(frm, cdt, cdn) {
		cur_frm.validate_row(frm, cdt, cdn)
	}
})
