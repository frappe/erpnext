frappe.ui.form.on("Payment Request", {
	setup(frm) {
		frm.set_query("party_type", function () {
			return {
				query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
			};
		});

		if (frm.fields_dict.payment_account) {
			frm.set_query("payment_account", function () {
				return {
					query: "erpnext.accounts.doctype.payment_request.payment_request.get_payment_account",
					filters: {
						payment_gateway: frm.doc.payment_gateway,
						company: frm.doc.company,
					},
				};
			});
		}

		if (frm.doc.payment_request_type == "Outward") {
			frm.set_query("bank_account", function () {
				return {
					filters: {
						party_type: frm.doc.party_type,
						party: frm.doc.party,
					},
				};
			});
		} else {
			frm.set_query("bank_account", function () {
				return {
					filters: {
						is_company_account: 1,
						company: frm.doc.company,
					},
				};
			});
		}
	},

	onload(frm) {
		if (frm.doc.reference_doctype) {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_request.payment_request.get_print_format_list",
				args: { ref_doctype: frm.doc.reference_doctype },
				callback: function (r) {
					set_field_options("print_format", r.message["print_format"]);
				},
			});
		}
	},

	refresh(frm) {
		if (frm.doc.status == "Failed") {
			frm.set_intro(__("Failure: {0}", [frm.doc.failed_reason]), "red");
		}

		let sending_email = false;

		if (
			frm.doc.payment_request_type == "Inward" &&
			frm.doc.payment_channel !== "Phone" &&
			!["Initiated", "Paid"].includes(frm.doc.status) &&
			!frm.doc.__islocal &&
			frm.doc.docstatus == 1
		) {
			frm.add_custom_button(__("Resend Payment Email"), function () {
				if (sending_email) {
					frappe.show_alert({ message: __("Sending Email"), indicator: "blue" });
					return;
				}
				sending_email = true;
				frappe.show_alert({ message: __("Sending Email"), indicator: "blue" });
				frm.call("resend_payment_email").then((r) => {
					const msg = !r.exc ? __("Email Sent") : __("Email couldn't be sent.");
					frappe.show_alert({ message: msg, indicator: !r.exc ? "green" : "red" });
					sending_email = false;
				});
			});
		}

		if (
			frm.doc.payment_request_type == "Outward" &&
			["Initiated", "Partially Paid"].includes(frm.doc.status)
		) {
			frm.add_custom_button(__("Create Payment Entry"), function () {
				frappe.call({
					method: "erpnext.accounts.doctype.payment_request.payment_request.make_payment_entry",
					args: { docname: frm.doc.name },
					freeze: true,
					callback: function (r) {
						if (!r.exc) {
							frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
					},
				});
			}).addClass("btn-primary");
		}
	},

	bank_account(frm) {
		if (frm.doc.bank_account) {
			frm.set_value("payment_gateway", null);
			frm.set_value("payment_account", null);
			frm.set_value("payment_channel", null);
			frm.set_value("phone_number", null);
		}
	},

	payment_gateway(frm) {
		if (frm.doc.payment_gateway) {
			frm.set_value("bank_account", null);
		}
		frm.set_value("payment_account", null);
		frm.set_value("payment_channel", null);
		frm.set_value("phone_number", null);
	},

	payment_account(frm) {
		if (!frm.doc.payment_gateway || !frm.doc.payment_account || !frm.doc.company) {
			frm.set_value("payment_channel", null);
			return;
		}

		frappe.db.get_value(
			"Payment Gateway Account",
			{
				parent: frm.doc.payment_gateway,
				payment_account: frm.doc.payment_account,
				company: frm.doc.company,
			},
			"payment_channel",
			(r) => {
				if (frm.fields_dict.payment_channel) {
					frm.set_value("payment_channel", r?.payment_channel || null);
				}
			},
			"Payment Gateway"
		);
	},

	is_a_subscription(frm) {
		if (frm.fields_dict.payment_gateway) {
			frm.toggle_reqd("payment_gateway", frm.doc.is_a_subscription);
		}

		frm.toggle_reqd("subscription_plans", frm.doc.is_a_subscription);

		if (frm.doc.is_a_subscription && frm.doc.reference_doctype && frm.doc.reference_name) {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_request.payment_request.get_subscription_details",
				args: {
					reference_doctype: frm.doc.reference_doctype,
					reference_name: frm.doc.reference_name,
				},
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
	},

	calculate_total_amount_by_selected_rows(frm) {
		if (frm.doc.docstatus !== 0) {
			frappe.msgprint(__("Cannot fetch selected rows for submitted Payment Request"));
			return;
		}

		const selected = frm.get_selected()?.payment_reference || [];

		if (!selected.length) {
			frappe.throw(__("No rows selected"));
		}

		let total = 0;

		selected.forEach((name) => {
			const row = frm.doc.payment_reference.find((d) => d.name === name);

			if (row) {
				row.manually_selected = 1;
				total += row.amount;
			}
		});

		frm.doc.payment_reference.forEach((row) => {
			row.auto_selected = 0;
		});

		frm.set_value("grand_total", total);
		frm.refresh_field("grand_total");
		frm.save();
	},
});
