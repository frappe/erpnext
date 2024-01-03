const itemDetailsCache = {};

export function fetchItemDetails(item_name, frm, callback) {
	if (itemDetailsCache[item_name]) {
		return callback(itemDetailsCache[item_name]);
	}
	frappe.call({
		method: "erpnext.stock.get_item_details.get_item_details",
		args: {
			args: {
				item_code: item_name,
				doctype: frm.doc.doctype,
				buying_price_list: frm.doc.selling_price_list,
				customer: frm.doc.customer,
				currency: frm.doc.currency,
				name: frm.doc.name,
				qty: 1,
				company: frm.doc.company,
			}
		},
		callback(r) {
			if (r.message) {
				itemDetailsCache[item_name] = r.message;
				callback(r.message);
			}
		}
	});
}
