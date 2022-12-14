// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
// Based on https://doku.phamos.eu/books/erpnext-handbuch-marius/page/dokumentenvorlage-am-beispiel-angebot, but in englisch and with error correction
// Features: Possible to create a templeate for a quotation. From the quotation form, the user cann load pre-defined items into the quotation
//			A multi-import is possible

frappe.ui.form.on('Quotation Template', {
	// refresh: function(frm) {

	// }
});


frappe.ui.form.on('Quotation', {
	refresh(frm) {
		frm.add_custom_button('Quotation Template', function () { frm.trigger('get_items') }, __("Get Items From"));
	},
	get_items(frm){
		start_dialog(frm);
	}
});

function start_dialog(frm) {

  var transaction_controller = new erpnext.TransactionController({ frm: frm });
	let dialog = new frappe.ui.form.MultiSelectDialog({

		// Read carefully and adjust parameters
		doctype: "Quotation Template", // Doctype we want to pick up
		target: frm,
		setters: {
			// MultiDialog Filterfields
			// customer: frm.doc.customer,
		},
		date_field: "creation", // "modified", "creation", ...
		get_query() {
			// MultiDialog Listfilter
			return {
				filters: {  }
			};
		},
	  action(selections) {
		  for(var n = 0; n < selections.length; n++){
			  var name = selections[n];
			  var items_idx = 0;
			  frappe.db.get_doc("Quotation Template", name) // Again, the Doctype we want to pick up
			  .then(doc => {
				  // Remove the first empty element of the table
				  try {
					  let last = frm.get_field("items").grid.grid_rows.length -1;
					  items_idx = last;
					  if(!('item_code' in frm.get_field("items").grid.grid_rows[last].doc)){
						  frm.get_field("items").grid.grid_rows[0].remove();
						  frm.refresh_fields("items");
					  }
				  } catch (error) {
					  console.log(error);
					  var row=frm.add_child("items"); // add row
					  frm.refresh_fields("items"); // Refresh Tabelle
				  }
					
				  // Run through all items of the template quotation
				  for(var k = 0; k < doc.quotation_template_item.length; k++){

					  // Declare variables and add table row
					  var item=doc.quotation_template_item[k];
					  var row=frm.add_child("items"); // add row
					  frm.refresh_fields("items"); // Refresh table
					  
					  // Copy-Paste Operation
					  let idx = items_idx+1;
					  let fields = ['item_code', 'qty'];
					  for(var m = 0; m < fields.length; m++){
						  frm.get_field("items").grid.grid_rows[idx].doc[fields[m]] = item[fields[m]];
						  frm.get_field("items").grid.grid_rows[idx].refresh_field(fields[m]);
					  }
					  frm.refresh_fields("items"); // Refresh table

					  // Get all other values from stock etc.
					  let quotation_doc = frm.doc;
					  let cdn = row.name;
					  transaction_controller.item_code(quotation_doc, "Quotation Item", cdn);
					  items_idx++;

				  }
			  });
		  }
	  }
  });
}
