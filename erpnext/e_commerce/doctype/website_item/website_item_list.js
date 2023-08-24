frappe.listview_settings['Website Item'] = {
	add_fields: ["item_name", "web_item_name", "published", "website_image", "has_variants", "variant_of"],
	filters: [["published", "=", "1"]],

	get_indicator: function(doc) {
		if (doc.has_variants && doc.published) {
			return [__("Template"), "orange", "has_variants,=,Yes|published,=,1"];
		} else if (doc.has_variants && !doc.published) {
			return [__("Template"), "grey", "has_variants,=,Yes|published,=,0"];
		} else if (doc.variant_of  && doc.published) {
			return [__("Variant"), "blue", "published,=,1|variant_of,=," + doc.variant_of];
		} else if (doc.variant_of  && !doc.published) {
			return [__("Variant"), "grey", "published,=,0|variant_of,=," + doc.variant_of];
		} else if (doc.published) {
			return [__("Published"), "green", "published,=,1"];
		} else {
			return [__("Not Published"), "grey", "published,=,0"];
		}
	}
};