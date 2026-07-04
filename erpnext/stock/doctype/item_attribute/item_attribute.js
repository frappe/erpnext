// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item Attribute", {
	numeric_values(frm) {
		// Numeric attributes have no discrete values; drop the rows so their
		// mandatory Attribute Value / Abbreviation don't block the save.
		if (frm.doc.numeric_values) {
			frm.clear_table("item_attribute_values");
			frm.refresh_field("item_attribute_values");
		}
	},
});
