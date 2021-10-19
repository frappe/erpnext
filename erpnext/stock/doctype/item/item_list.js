frappe.listview_settings['Item'] = {
	add_fields: ["item_name", "stock_uom", "item_group", "image", "variant_of",
		"has_variants", "end_of_life", "disabled"],
	filters: [["disabled", "=", "0"]],

	get_indicator: function(doc) {
		if (doc.disabled) {
			return [__("Disabled"), "grey", "disabled,=,Yes"];
		} else if (doc.end_of_life && doc.end_of_life < frappe.datetime.get_today()) {
			return [__("Expired"), "grey", "end_of_life,<,Today"];
		} else if (doc.has_variants) {
			return [__("Template"), "orange", "has_variants,=,Yes"];
		} else if (doc.variant_of) {
			return [__("Variant"), "green", "variant_of,=," + doc.variant_of];
		}
	},
	onload: function(me) {
		me.page.add_action_item(__("Create Website Item(s)"), function() {
			const items = me.get_checked_items().map(item => item.name);
			frappe.call({
				method: "erpnext.e_commerce.doctype.website_item.website_item.make_bulk_website_items",
				args: {items: items},
				freeze: true,
				freeze_message: __("Publishing Items ..."),
				callback(results) {
					results.message.forEach(result => {
						frappe.msgprint({
							message: __("Website Item {0} has been created.",
								[repl('<a href="/app/website-item/%(item_encoded)s" class="strong">%(item)s</a>', {
									item_encoded: encodeURIComponent(result[0]),
									item: result[1]
								})]
							),
							title: __("Published"),
							indicator: "green"
						});
					});
				}
			});
		});
	},

	reports: [
		{
			name: 'Stock Summary',
			report_type: 'Page',
			route: 'stock-balance'
		},
		{
			name: 'Stock Ledger',
			report_type: 'Script Report'
		},
		{
			name: 'Stock Balance',
			report_type: 'Script Report'
		},
		{
			name: 'Stock Projected Qty',
			report_type: 'Script Report'
		}

	]
};

frappe.help.youtube_id["Item"] = "qXaEwld4_Ps";
