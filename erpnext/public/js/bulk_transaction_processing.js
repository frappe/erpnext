frappe.provide("erpnext.bulk_transaction_processing");

$.extend(erpnext.bulk_transaction_processing, {
	create: function (listview, from_doctype, to_doctype) {
		let checked_items = listview.get_checked_items();
		const doc_name = [];
		checked_items.forEach((Item) => {
			if (Item.docstatus == 0) {
				doc_name.push(Item.name);
			}
		});

		let count_of_rows = checked_items.length;
		frappe.confirm(__("Create {0} {1} ?", [count_of_rows, __(to_doctype)]), () => {
			if (doc_name.length == 0) {
				frappe
					.call({
						method: "erpnext.utilities.bulk_transaction.transaction_processing",
						args: { data: checked_items, from_doctype: from_doctype, to_doctype: to_doctype },
					})
					.then(() => {});
				if (count_of_rows > 10) {
					frappe.show_alert("Starting a background job to create {0} {1}", [
						count_of_rows,
						__(to_doctype),
					]);
				}
			} else {
				frappe.msgprint(__("Selected document must be in submitted state"));
			}
		});
	},
});
