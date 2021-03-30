frappe.ui.form.on("Issue", {
	onload: function(frm) {
		frm.email_field = "raised_by";
		frm.set_query("customer", function () {
			return {
				filters: {
					"disabled": 0
				}
			};
		});

		frappe.db.get_value("Support Settings", {name: "Support Settings"},
			["allow_resetting_service_level_agreement", "track_service_level_agreement"], (r) => {
				if (r && r.track_service_level_agreement == "0") {
					frm.set_df_property("service_level_section", "hidden", 1);
				}
				if (r && r.allow_resetting_service_level_agreement == "0") {
					frm.set_df_property("reset_service_level_agreement", "hidden", 1);
				}
		});

		if (frm.doc.service_level_agreement) {
			frappe.call({
				method: "erpnext.support.doctype.service_level_agreement.service_level_agreement.get_service_level_agreement_filters",
				args: {
					name: frm.doc.service_level_agreement,
					customer: frm.doc.customer
				},
				callback: function (r) {
					if (r && r.message) {
						frm.set_query("priority", function() {
							return {
								filters: {
									"name": ["in", r.message.priority],
								}
							};
						});
						frm.set_query("service_level_agreement", function() {
							return {
								filters: {
									"name": ["in", r.message.service_level_agreements],
								}
							};
						});
					}
				}
			});
		}
	},

	refresh: function (frm) {
		if (frm.doc.status !== "Closed") {
			if (frm.doc.service_level_agreement && frm.doc.agreement_status === "Ongoing") {
				frappe.call({
					"method": "frappe.client.get",
					args: {
						doctype: "Service Level Agreement",
						name: frm.doc.service_level_agreement
					},
					callback: function(data) {
						let statuses = data.message.pause_sla_on;
						const hold_statuses = [];
						$.each(statuses, (_i, entry) => {
							hold_statuses.push(entry.status);
						});
						if (hold_statuses.includes(frm.doc.status)) {
							frm.dashboard.clear_headline();
							let message = {"indicator": "orange", "msg": __("SLA is on hold since {0}", [moment(frm.doc.on_hold_since).fromNow(true)])};
							frm.dashboard.set_headline_alert(
								'<div class="row">' +
									'<div class="col-xs-12">' +
										'<span class="indicator whitespace-nowrap '+ message.indicator +'"><span>'+ message.msg +'</span></span> ' +
									'</div>' +
								'</div>'
							);
						} else {
							set_time_to_resolve_and_response(frm);
						}
					}
				});
			}

			frm.add_custom_button(__("Close"), function () {
				frm.set_value("status", "Closed");
				frm.save();
			});

			frm.add_custom_button(__("Task"), function () {
				frappe.model.open_mapped_doc({
					method: "erpnext.support.doctype.issue.issue.make_task",
					frm: frm
				});
			}, __("Create"));

		} else {
			if (frm.doc.service_level_agreement) {
				frm.dashboard.clear_headline();

				let agreement_status = (frm.doc.agreement_status == "Fulfilled") ?
					{"indicator": "green", "msg": "Service Level Agreement has been fulfilled"} :
					{"indicator": "red", "msg": "Service Level Agreement Failed"};

				frm.dashboard.set_headline_alert(
					'<div class="row">' +
						'<div class="col-xs-12">' +
							'<span class="indicator whitespace-nowrap '+ agreement_status.indicator +'"><span class="hidden-xs">'+ agreement_status.msg +'</span></span> ' +
						'</div>' +
					'</div>'
				);
			}

			frm.add_custom_button(__("Reopen"), function () {
				frm.set_value("status", "Open");
				frm.save();
			});
		}
	},

	reset_service_level_agreement: function(frm) {
		let reset_sla = new frappe.ui.Dialog({
			title: __("Reset Service Level Agreement"),
			fields: [
				{
					fieldtype: "Data",
					fieldname: "reason",
					label: __("Reason"),
					reqd: 1
				}
			],
			primary_action_label: __("Reset"),
			primary_action: (values) => {
				reset_sla.disable_primary_action();
				reset_sla.hide();
				reset_sla.clear();

				frappe.show_alert({
					indicator: "green",
					message: __("Resetting Service Level Agreement.")
				});

				frm.call("reset_service_level_agreement", {
					reason: values.reason,
					user: frappe.session.user_email
				}, () => {
					reset_sla.enable_primary_action();
					frm.refresh();
					frappe.msgprint(__("Service Level Agreement was reset."));
				});
			}
		});

		reset_sla.show();
	},


	timeline_refresh: function(frm) {
		if (!frm.timeline.wrapper.find(".btn-split-issue").length) {
			let split_issue_btn = $(`
				<a class="action-btn btn-split-issue" title="${__("Split Issue")}">
					${frappe.utils.icon('branch', 'sm')}
				</a>
			`);

			let communication_box = frm.timeline.wrapper.find('.timeline-item[data-doctype="Communication"]');
			communication_box.find('.actions').prepend(split_issue_btn);

			if (!frm.timeline.wrapper.data("split-issue-event-attached")) {
				frm.timeline.wrapper.on('click', '.btn-split-issue', (e) => {
					var dialog = new frappe.ui.Dialog({
						title: __("Split Issue"),
						fields: [
							{
								fieldname: "subject",
								fieldtype: "Data",
								reqd: 1,
								label: __("Subject"),
								description: __("All communications including and above this shall be moved into the new Issue")
							}
						],
						primary_action_label: __("Split"),
						primary_action: () => {
							frm.call("split_issue", {
								subject: dialog.fields_dict.subject.value,
								communication_id: e.currentTarget.closest(".timeline-item").getAttribute("data-name")
							}, (r) => {
								frappe.msgprint(`New issue created: <a href="/app/issue/${r.message}">${r.message}</a>`);
								frm.reload_doc();
								dialog.hide();
							});
						}
					});
					dialog.show();
				});
				frm.timeline.wrapper.data("split-issue-event-attached", true);
			}
		}

		// create button for "Help Article"
		// if (frappe.model.can_create("Help Article")) {
		// 	// Removing Help Article button if exists to avoid multiple occurrence
		// 	frm.timeline.wrapper.find('.action-btn .btn-add-to-kb').remove();

		// 	let help_article = $(`
		// 		<a class="action-btn btn-add-to-kb" title="${__('Help Article')}">
		// 			${frappe.utils.icon('solid-info', 'sm')}
		// 		</a>
		// 	`);

		// 	let communication_box = frm.timeline.wrapper.find('.timeline-item[data-doctype="Communication"]');
		// 	communication_box.find('.actions').prepend(help_article);
		// 	if (!frm.timeline.wrapper.data("help-article-event-attached")) {
		// 		frm.timeline.wrapper.on('click', '.btn-add-to-kb', function () {
		// 			const content = $(this).parents('.timeline-item[data-doctype="Communication"]:first').find(".content").html();
		// 			const doc = frappe.model.get_new_doc("Help Article");
		// 			doc.title = frm.doc.subject;
		// 			doc.content = content;
		// 			frappe.set_route("Form", "Help Article", doc.name);
		// 		});
		// 	}
		// 	frm.timeline.wrapper.data("help-article-event-attached", true);
		// }
	},
});

function set_time_to_resolve_and_response(frm) {
	frm.dashboard.clear_headline();

	var time_to_respond = get_status(frm.doc.response_by_variance);
	if (!frm.doc.first_responded_on && frm.doc.agreement_status === "Ongoing") {
		time_to_respond = get_time_left(frm.doc.response_by, frm.doc.agreement_status);
	}

	var time_to_resolve = get_status(frm.doc.resolution_by_variance);
	if (!frm.doc.resolution_date && frm.doc.agreement_status === "Ongoing") {
		time_to_resolve = get_time_left(frm.doc.resolution_by, frm.doc.agreement_status);
	}

	frm.dashboard.set_headline_alert(
		'<div class="row">' +
			'<div class="col-xs-12 col-sm-6">' +
				'<span class="indicator whitespace-nowrap '+ time_to_respond.indicator +'"><span>Time to Respond: '+ time_to_respond.diff_display +'</span></span> ' +
			'</div>' +
			'<div class="col-xs-12 col-sm-6">' +
				'<span class="indicator whitespace-nowrap '+ time_to_resolve.indicator +'"><span>Time to Resolve: '+ time_to_resolve.diff_display +'</span></span> ' +
			'</div>' +
		'</div>'
	);
}

function get_time_left(timestamp, agreement_status) {
	const diff = moment(timestamp).diff(moment());
	const diff_display = diff >= 44500 ? moment.duration(diff).humanize() : "Failed";
	let indicator = (diff_display == "Failed" && agreement_status != "Fulfilled") ? "red" : "green";
	return {"diff_display": diff_display, "indicator": indicator};
}

function get_status(variance) {
	if (variance > 0) {
		return {"diff_display": "Fulfilled", "indicator": "green"};
	} else {
		return {"diff_display": "Failed", "indicator": "red"};
	}
}
