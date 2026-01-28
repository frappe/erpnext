// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subscription", {
	onload: function (frm) {
		frm.trigger("render_heatmap");
	},
	setup: function (frm) {
		frm.set_query("party_type", function () {
			return {
				filters: {
					name: ["in", ["Customer", "Supplier"]],
				},
			};
		});

		frm.set_query("cost_center", function () {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("sales_tax_template", function () {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
		});
	},

	refresh: function (frm) {
		frm.trigger("get_amount_details");
		if (frm.is_new()) return;

		if (frm.doc.status !== "Cancelled") {
			frm.add_custom_button(
				__("Fetch Subscription Updates"),
				() => frm.trigger("get_subscription_updates"),
				__("Actions")
			);

			frm.add_custom_button(
				__("Force-Fetch Subscription Updates"),
				() => frm.trigger("force_fetch_subscription_updates"),
				__("Actions")
			);

			frm.add_custom_button(
				__("Cancel Subscription"),
				() => frm.trigger("cancel_this_subscription"),
				__("Actions")
			);
		} else if (frm.doc.status === "Cancelled") {
			frm.add_custom_button(
				__("Restart Subscription"),
				() => frm.trigger("renew_this_subscription"),
				__("Actions")
			);
		}
	},

	cancel_this_subscription: function (frm) {
		frappe.confirm(
			__("This action will stop future billing. Are you sure you want to cancel this subscription?"),
			() => {
				frm.call("cancel_subscription").then((r) => {
					if (!r.exec) {
						frm.reload_doc();
					}
				});
			}
		);
	},

	renew_this_subscription: function (frm) {
		frappe.confirm(__("Are you sure you want to restart this subscription?"), () => {
			frm.call("restart_subscription").then((r) => {
				if (!r.exec) {
					frm.reload_doc();
				}
			});
		});
	},

	get_subscription_updates: function (frm) {
		frm.call("process").then((r) => {
			if (!r.exec) {
				frm.reload_doc();
			}
		});
	},
	force_fetch_subscription_updates: function (frm) {
		frm.call("force_fetch_subscription_updates").then((r) => {
			if (!r.exec) {
				frm.reload_doc();
			}
		});
	},
	render_heatmap(frm) {
		let subscription_heatmap = frm.get_field("subscription_heatmap").$wrapper;
		subscription_heatmap.addClass("subscription_heatmap_location");

		// Fetch paid sales cycles from the server
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Sales Invoice",
				filters: {
					subscription: frm.doc.name,
					docstatus: 1,
				},
				fields: ["from_date", "to_date", "status"],
				limit_page_length: 365,
			},
			callback: function (r) {
				let datapoints = {};
				let msiad = 86400000; // 1 day

				let start = frappe.datetime.str_to_obj(frm.doc.start_date);
				let end = frm.doc.end_date
					? frappe.datetime.str_to_obj(frm.doc.end_date)
					: frappe.datetime.str_to_obj(frappe.datetime.nowdate());

				for (let d = new Date(start); d <= end; d.setTime(d.getTime() + msiad)) {
					datapoints[Math.floor(d.getTime() / 1000)] = 0;
				}

				(r.message || []).forEach((inv) => {
					if (inv.status !== "Paid") return;

					let from = frappe.datetime.str_to_obj(inv.from_date);
					let to = frappe.datetime.str_to_obj(inv.to_date);

					for (let d = new Date(from); d <= to; d.setTime(d.getTime() + msiad)) {
						let key = Math.floor(d.getTime() / 1000);
						if (key in datapoints) datapoints[key] = 1;
					}
				});

				new frappe.Chart(".subscription_heatmap_location", {
					type: "heatmap",
					data: {
						dataPoints: datapoints,
						start: new Date(frm.doc.start_date),
						end: new Date(frm.doc.end_date || frappe.datetime.nowdate()),
					},
					countLabel: "Active Subscription",
					discreteDomains: 1,
				});
			},
		});
		return;
	},
	get_amount_details(frm) {
		frm.call("get_amount_details").then((r) => {
			if (r.message) {
				for (let row of r.message) {
					let plan_row = frm.doc.plans.find((plan) => plan.plan == row.plan);
					if (plan_row) {
						plan_row.amount = row.amount;
					}
				}
				frm.refresh_field("plans");
			}
		});
	},
});
