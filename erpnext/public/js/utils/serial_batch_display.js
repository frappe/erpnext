const title_requests = new Map();

export function format_serial_numbers(value, df, _options, row) {
	value = row?.[df.fieldname] ?? value;
	if (erpnext.serial_batch_input.is_pending(row, df.fieldname)) {
		return frappe.utils.escape_html(value || "").replace(/\n/g, "<br>");
	}
	const key = encodeURIComponent(value || "");
	load_serial_titles(value).then(() => {
		$(`[data-serial-number-list="${key}"]`).text(serial_number_text(value));
	});
	return `<span data-serial-number-list="${key}" style="white-space: pre-line">${frappe.utils.escape_html(
		serial_number_text(value)
	)}</span>`;
}

export function serial_number_text(value) {
	return (value || "")
		.split("\n")
		.map((id) => frappe.utils.get_link_title("Serial No", id) || id)
		.join("\n");
}

export async function load_serial_titles(value) {
	const missing = (value || "")
		.split("\n")
		.filter((id) => id && !frappe.utils.get_link_title("Serial No", id));
	if (!missing.length) return;
	const key = JSON.stringify(missing);
	if (!title_requests.has(key)) {
		title_requests.set(
			key,
			frappe
				.xcall("erpnext.stock.serial_batch_identity.get_serial_batch_labels", {
					doctype: "Serial No",
					names: missing,
				})
				.then((labels) => {
					missing.forEach((id) => frappe.utils.add_link_title("Serial No", id, labels[id] || id));
				})
				.finally(() => title_requests.delete(key))
		);
	}
	return title_requests.get(key);
}

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
