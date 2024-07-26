cur_frm.add_fetch("payment_gateway_account", "payment_account", "payment_account");
cur_frm.add_fetch("payment_gateway_account", "payment_gateway", "payment_gateway");
cur_frm.add_fetch("payment_gateway_account", "message", "message");

frappe.ui.form.on("Payment Request", {
	setup: function (frm) {
		frm.set_query("party_type", function () {
			return {
				query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
			};
		});
	},
});

frappe.ui.form.on("Payment Request", "onload", function (frm, dt, dn) {
	if (frm.doc.reference_doctype) {
		frappe.call({
			method: "erpnext.accounts.doctype.payment_request.payment_request.get_print_format_list",
			args: { ref_doctype: frm.doc.reference_doctype },
			callback: function (r) {
				set_field_options("print_format", r.message["print_format"]);
			},
		});
	}
});

frappe.ui.form.on("Payment Request", "refresh", function (frm) {
	if (frm.doc.status == "Failed") {
		frm.set_intro(__("Failure: {0}", [frm.doc.failed_reason]), "red");
	}

	if (
		frm.doc.payment_request_type == "Inward" &&
		frm.doc.payment_channel !== "Phone" &&
		!["Initiated", "Paid"].includes(frm.doc.status) &&
		!frm.doc.__islocal &&
		frm.doc.docstatus == 1
	) {
		frm.add_custom_button(__("Resend Payment Email"), function () {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_request.payment_request.resend_payment_email",
				args: { docname: frm.doc.name },
				freeze: true,
				freeze_message: __("Sending"),
				callback: function (r) {
					if (!r.exc) {
						frappe.msgprint(__("Message Sent"));
					}
				},
			});
		});
	}

	if (
		(!frm.doc.payment_gateway_account || frm.doc.payment_request_type == "Outward") &&
		frm.doc.status == "Initiated"
	) {
		frm.add_custom_button(__("Create Payment Entry"), function () {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_request.payment_request.make_payment_entry",
				args: { docname: frm.doc.name },
				freeze: true,
				callback: function (r) {
					if (!r.exc) {
						var doc = frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				},
			});
		}).addClass("btn-primary");
	}
});

frappe.ui.form.on("Payment Request", "is_a_subscription", function (frm) {
	frm.toggle_reqd("payment_gateway_account", frm.doc.is_a_subscription);
	frm.toggle_reqd("subscription_plans", frm.doc.is_a_subscription);

	if (frm.doc.is_a_subscription && frm.doc.reference_doctype && frm.doc.reference_name) {
		frappe.call({
			method: "erpnext.accounts.doctype.payment_request.payment_request.get_subscription_details",
			args: { reference_doctype: frm.doc.reference_doctype, reference_name: frm.doc.reference_name },
			freeze: true,
			callback: function (data) {
				if (!data.exc) {
					$.each(data.message || [], function (i, v) {
						var d = frappe.model.add_child(
							frm.doc,
							"Subscription Plan Detail",
							"subscription_plans"
						);
						d.qty = v.qty;
						d.plan = v.plan;
					});
					frm.refresh_field("subscription_plans");
				}
			},
		});
	}
});
