// Reports export physical numbers and retain a separate ID field for each link.
frappe.form.formatters.SerialBatchNumber = (value, df, options, doc) => {
	if (!value) return "";
	const labels = String(value).split("\n");
	const ids = String(doc?.[df.reference_field] || "").split("\n");
	return labels
		.map((label, index) => {
			if (
				!ids[index] ||
				options?.for_print ||
				options?.only_value ||
				!frappe.model.can_read(df.options)
			) {
				return frappe.utils.escape_html(label);
			}
			return frappe.form.formatters.Link(ids[index], df, { ...options, label }, doc);
		})
		.join("<br>");
};
