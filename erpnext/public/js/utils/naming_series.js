const full_options = {};

function get_full_options(doctype) {
	if (!(doctype in full_options)) {
		const df = frappe.meta.get_docfield(doctype, "naming_series");
		full_options[doctype] = (df?.options || "").split("\n").filter(Boolean);
	}
	return full_options[doctype];
}

function apply_options(frm, options) {
	frm.set_df_property("naming_series", "options", options.join("\n"));
	if (!options.includes(frm.doc.naming_series)) {
		frm.set_value("naming_series", options[0]);
	}
}

function set_naming_series_options(frm) {
	if (!frm.is_new() || !frm.fields_dict.naming_series || !frm.doc.company) return;

	const company = frm.doc.company;
	const fallback = get_full_options(frm.doctype);

	frappe
		.xcall(
			"erpnext.setup.doctype.company_naming_series.company_naming_series.get_naming_series_options",
			{ company: company, doctype: frm.doctype }
		)
		.then((allowed) => {
			if (frm.doc.company !== company) return;

			const options = allowed.length ? allowed : fallback;
			if (options.length) {
				apply_options(frm, options);
			}
		});
}

frappe.ui.form.on("*", {
	onload: set_naming_series_options,
	company: set_naming_series_options,
});
