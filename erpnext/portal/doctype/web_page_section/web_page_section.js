// For license information, please see license.txt

frappe.ui.form.on("Web Page Section", {
	onload: function(frm) {
		frm.set_query("content_document", "items", function(doc, cdt, cdn) {
			const item = locals[cdt][cdn];

			if (item.content_doctype==="Blog Post") {
				return { filters: {'published': 1} };
			} else if (item.content_doctype==="Item") {
				return { filters: {'show_in_website': 1} };
			} else {
				return {};
			}
		});
	}
});
