frappe.listview_settings['Item'] = {
	add_fields: ["item_name", "stock_uom", "item_group", "image", "variant_of", "has_variants"],
	get_indicator: function(doc) {
		if(doc.has_variants) {
			return [__("Template"), "blue", "has_variant,=,1"]
		} else if(doc.variant_of) {
			return [__("Variant"), "green", "variant_of,=," + doc.variant_of]
		}
	}
};
