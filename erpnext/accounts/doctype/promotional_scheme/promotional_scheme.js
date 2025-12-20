// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Promotional Scheme", {
	setup: function (frm) {
		frm.set_query("for_price_list", "price_discount_slabs", (doc) => {
			return {
				filters: {
					selling: doc.selling,
					buying: doc.buying,
					currency: doc.currency,
				},
			};
		});
	},

	refresh: function (frm) {
		frm.trigger("set_options_for_applicable_for");
		frm.trigger("toggle_reqd_apply_on");
	},

	selling: function (frm) {
		frm.trigger("set_options_for_applicable_for");
	},

	buying: function (frm) {
		frm.trigger("set_options_for_applicable_for");
	},

	set_options_for_applicable_for: function (frm) {
		var options = [""];
		var applicable_for = frm.doc.applicable_for;

		if (frm.doc.selling) {
			options = $.merge(options, [
				"Customer",
				"Customer Group",
				"Territory",
				"Sales Partner",
				"Campaign",
			]);
		}
		if (frm.doc.buying) {
			$.merge(options, ["Supplier", "Supplier Group"]);
		}

		set_field_options("applicable_for", options.join("\n"));

		if (!in_list(options, applicable_for)) applicable_for = null;
		frm.set_value("applicable_for", applicable_for);
	},

	apply_on: function (frm) {
		frm.trigger("toggle_reqd_apply_on");
	},

	toggle_reqd_apply_on: function (frm) {
		const fields = {
			"Item Code": "items",
			"Item Group": "item_groups",
			Brand: "brands",
		};

		for (var key in fields) {
			frm.toggle_reqd(fields[key], frm.doc.apply_on === key ? 1 : 0);
		}
	},
});
