// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subscription", {
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
		if (frm.is_new()) {
			// The field wrapper is reused across docs; clear any stale heatmap.
			frm.get_field("billing_heatmap").$wrapper.empty();
			return;
		}

		frm.trigger("render_billing_heatmap");

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

	render_billing_heatmap: function (frm) {
		frm.call("get_billing_heatmap").then((r) => {
			if (!r.message || !r.message.length) return;
			render_heatmap(frm.get_field("billing_heatmap").$wrapper, r.message, frm.doc);
		});
	},
});

// Status -> colour and label for the calendar heatmap. Keys are Title-case to
// match the value frappe-charts shows in its hover tooltip.
const HEATMAP_COLORS = {
	Paid: "#39d353",
	Unpaid: "#388bfd",
	Overdue: "#f0883e",
	Cancelled: "#f85149",
	Refunded: "#a371f7",
	Planned: "#87ceeb",
};

// Days inside the window but outside the subscription's active span stay faded.
const EMPTY_COLOR = "#ebedf0";

function title_case(status) {
	return status.charAt(0).toUpperCase() + status.slice(1);
}

function render_heatmap($wrapper, days, doc) {
	const data_points = {};
	days.forEach((day) => {
		data_points[day.date] = title_case(day.status);
	});

	$wrapper.empty();
	const chart_el = $('<div class="subscription-billing-heatmap"></div>').appendTo($wrapper)[0];

	new frappe.Chart(chart_el, {
		type: "heatmap",
		data: {
			dataPoints: data_points,
			start: new Date(days[0].date),
			end: new Date(days[days.length - 1].date),
		},
		discreteDomains: 1,
		showLegend: 0,
		// frappe-charts only does an intensity scale; we recolour each square by
		// its own status below, so the scale colours are placeholders.
		colors: ["#ebedf0", "#ebedf0", "#ebedf0", "#ebedf0", "#ebedf0"],
	});

	// Paint every day square with its status colour (data-value holds the status).
	// The chart re-renders once for its entry animation, so repaint on each redraw.
	const within_subscription = (date) =>
		(!doc.start_date || date >= doc.start_date) && (!doc.end_date || date <= doc.end_date);

	const paint = () =>
		chart_el.querySelectorAll("[data-date]").forEach((square) => {
			const status = square.getAttribute("data-value");
			if (status === "Planned" && !within_subscription(square.getAttribute("data-date"))) {
				// Outside the subscription's span: render blank and drop the status so the
				// hover tooltip shows only the date, not "Planned".
				square.setAttribute("fill", EMPTY_COLOR);
				square.setAttribute("data-value", "");
				return;
			}
			square.setAttribute("fill", HEATMAP_COLORS[status] || EMPTY_COLOR);
		});

	paint();
	new MutationObserver(paint).observe(chart_el, { childList: true, subtree: true });

	const legend = Object.keys(HEATMAP_COLORS)
		.map(
			(status) =>
				`<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px;">
					<span style="width:11px;height:11px;border-radius:2px;background:${HEATMAP_COLORS[status]};"></span>
					${__(status)}
				</span>`
		)
		.join("");

	$(`<div style="margin-top:8px;font-size:11px;color:var(--text-muted);">${legend}</div>`).appendTo(
		$wrapper
	);
}
