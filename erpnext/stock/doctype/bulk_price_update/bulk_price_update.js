// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Price Update', {
	refresh: function(frm) {
		frm.disable_save();
		frm.events.set_primary_action(frm);
		frm.events.add_remove_missing_items_button(frm);
	},

	onload: function(frm) {
		frm.set_query("item_code", "items", function() {
			return erpnext.queries.item();
		});
	},

	set_primary_action: function(frm) {
		frm.page.set_primary_action(__("Update"), function() {
			frm.call({
				method: "update_prices",
				doc: frm.doc,
				freeze: 1,
				freeze_message: __("Updating Prices..."),
				callback: function(r) {
					frm.refresh_fields();
				}
			});
		});
	},

	effective_date: function (frm) {
		frm.events.get_current_rates(frm);
	},

	price_list: function (frm) {
		if (frm.doc.price_list) {
			$.each(frm.doc.items || [], function (i, d) {
				var doc = frappe.get_doc(d.doctype, d.name);
				doc.price_list = frm.doc.price_list;
			});
			refresh_field('price_list', null, 'items');
		}
		frm.events.get_current_rates(frm);
	},

	items_after_bulk_upload: function (frm) {
		frm.events.set_missing_price_list(frm);
		frm.events.get_current_rates(frm);
	},

	get_current_rates: function (frm, row) {
		var run;
		if (row) {
			run = row.item_code && frm.events.get_price_list(frm, row) ? 1 : 0;
		} else {
			var valid_rows = (frm.doc.items || []).filter(d => d.item_code && frm.events.get_price_list(frm, d));
			run = valid_rows.length ? 1 : 0;
		}

		if (!run) {
			return;
		}

		frm.call({
			method: "get_current_rates",
			doc: frm.doc,
			args: {
				row: row && row.name || null
			},
			callback: function () {
				frm.refresh_fields();
			}
		});
	},

	get_price_list: function (frm, row) {
		return frm.doc.price_list || (row && row.price_list);
	},

	set_missing_price_list: function (frm) {
		if (frm.doc.price_list) {
			$.each(frm.doc.items || [], function (i, d) {
				if (!d.price_list) {
					d.price_list = frm.doc.price_list;
				}
			});
		}
		frm.refresh_field('items');
	},

	add_remove_missing_items_button: function (frm) {
		frm.fields_dict.items.grid.add_custom_button(__("Remove Missing Items"),  function () {
			var actions = [];
			$.each(frm.doc.items || [], function(i, d) {
				if (!d.item_code) {
					actions.push(() => frm.fields_dict.items.grid.get_row(d.name).remove());
				}
			});

			return frappe.run_serially(actions);
		});
	},
});

frappe.ui.form.on('Bulk Price Detail', {
	item_code: function (frm, cdt, cdn) {
		var doc = frappe.get_doc(cdt, cdn);
		frm.events.get_current_rates(frm, doc);
	},

	price_list: function (frm, cdt, cdn) {
		var doc = frappe.get_doc(cdt, cdn);
		frm.events.get_current_rates(frm, doc);
	},

	items_add: function (frm, cdt, cdn) {
		if (frm.doc.price_list) {
			var doc = frappe.get_doc(cdt, cdn);
			doc.price_list = frm.doc.price_list;
			refresh_field('price_list', cdn, 'items');
		}
	},
});
