// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Settings", {
	refresh: function (frm) {
		let filters = function () {
			return {
				filters: {
					is_group: 0,
				},
			};
		};

		frm.set_query("default_warehouse", filters);
		frm.set_query("sample_retention_warehouse", filters);

		if (!frm.naming_controller) frm.naming_controller = new erpnext.NamingSeriesController(frm);
		const item_display = frm.doc.item_naming_by === "Naming Series";
		const serial_and_batch_naming_display =
			frm.doc.set_serial_and_batch_bundle_naming_based_on_naming_series;

		frm.set_df_property("naming_series_details", "hidden", !item_display);
		frm.set_df_property("configure", "hidden", !item_display);
		frm.set_df_property("naming_series_preview", "hidden", !serial_and_batch_naming_display);
		frm.set_df_property("configure_series", "hidden", !serial_and_batch_naming_display);

		if (item_display) {
			frm.naming_controller.load_master_series("Item", "naming_series_details");
		} else {
			frm.doc.naming_series_details = "";
		}

		if (serial_and_batch_naming_display) {
			frm.naming_controller.load_master_series("Serial and Batch Bundle", "naming_series_preview");
		} else {
			frm.doc.naming_series_preview = "";
		}

		frm.naming_controller.render_table("transaction_naming_html", get_transactions(frm));
	},

	item_naming_by(frm) {
		const display = frm.doc.item_naming_by === "Naming Series";
		frm.set_df_property("naming_series_details", "hidden", !display);
		frm.set_df_property("configure", "hidden", !display);

		if (display) {
			frm.naming_controller.load_master_series("Item", "naming_series_details");
		} else {
			frm.doc.naming_series_details = "";
			frm.refresh_field("naming_series_details");
		}

		frm.naming_controller.render_table("transaction_naming_html", get_transactions(frm));
	},

	set_serial_and_batch_bundle_naming_based_on_naming_series(frm) {
		const display = frm.doc.set_serial_and_batch_bundle_naming_based_on_naming_series;
		frm.set_df_property("naming_series_preview", "hidden", !display);
		frm.set_df_property("configure_series", "hidden", !display);
		if (display) {
			frm.naming_controller.load_master_series("Serial and Batch Bundle", "naming_series_preview");
		} else {
			frm.doc.naming_series_preview = "";
			frm.refresh_field("naming_series_preview");
		}
	},

	configure(frm) {
		configure_naming_series(frm, "Item", "naming_series_details");
	},

	configure_series(frm) {
		configure_naming_series(frm, "Serial and Batch Bundle", "naming_series_preview");
	},

	enable_serial_and_batch_no_for_item(frm) {
		if (frm.doc.enable_serial_and_batch_no_for_item) {
			frappe.msgprint(__("After save, please refresh the page to apply the changes."));
		}
	},

	use_serial_batch_fields(frm) {
		if (frm.doc.use_serial_batch_fields && !frm.doc.disable_serial_no_and_batch_selector) {
			frm.set_value("disable_serial_no_and_batch_selector", 1);
		}
	},

	disable_serial_no_and_batch_selector(frm) {
		if (!frm.doc.disable_serial_no_and_batch_selector && frm.doc.use_serial_batch_fields) {
			frm.set_value("disable_serial_no_and_batch_selector", 1);
			frappe.msgprint(
				__("Serial No and Batch Selector cannot be use when Use Serial / Batch Fields is enabled.")
			);
		}
	},

	allow_negative_stock: function (frm) {
		if (!frm.doc.allow_negative_stock) {
			return;
		}

		let msg = __(
			"Using negative stock disables FIFO/Moving average valuation when inventory is negative."
		);
		msg += " ";
		msg += __("This is considered dangerous from accounting point of view.");
		msg += "<br>";
		msg += __("Do you still want to enable negative inventory?");

		frappe.confirm(
			msg,
			() => {},
			() => {
				frm.set_value("allow_negative_stock", 0);
			}
		);
	},
	auto_insert_price_list_rate_if_missing(frm) {
		if (!frm.doc.auto_insert_price_list_rate_if_missing) return;

		frm.set_value(
			"update_price_list_based_on",
			cint(frappe.defaults.get_default("editable_price_list_rate")) ? "Price List Rate" : "Rate"
		);
	},
	update_price_list_based_on(frm) {
		if (
			frm.doc.update_price_list_based_on === "Price List Rate" &&
			!cint(frappe.defaults.get_default("editable_price_list_rate"))
		) {
			const dialog = frappe.warn(
				__("Incompatible Setting Detected"),
				__(
					"<p>Price List Rate has not been set as editable in Selling Settings. In this scenario, setting <strong>Update Price List Based On</strong> to <strong>Price List Rate</strong> will prevent auto-updation of Item Price.</p>Are you sure you want to continue?"
				)
			);
			dialog.set_secondary_action(() => {
				frm.set_value("update_price_list_based_on", "Rate");
				dialog.hide();
			});
			return;
		}
	},
});

function get_transactions(frm) {
	const transactions = [
		{ label: __("Item"), doctype: "Item" },
		{ label: __("Stock Entry"), doctype: "Stock Entry" },
		{ label: __("Purchase Receipt"), doctype: "Purchase Receipt" },
		{ label: __("Delivery Note"), doctype: "Delivery Note" },
		{ label: __("Material Request"), doctype: "Material Request" },
		{ label: __("Pick List"), doctype: "Pick List" },
		{ label: __("Stock Reconciliation"), doctype: "Stock Reconciliation" },
		{ label: __("Serial and Batch Bundle"), doctype: "Serial and Batch Bundle" },
	];

	if (frm.doc.item_naming_by !== "Naming Series") {
		return transactions.filter((t) => t.doctype !== "Item");
	}

	return transactions;
}

function configure_naming_series(frm, doctype, fieldname) {
	frm.naming_controller.show_naming_series_dialog(doctype, ({ naming_series_options }) => {
		frm.doc[fieldname] = naming_series_options;
		frm.refresh_field(fieldname);
	});
}
