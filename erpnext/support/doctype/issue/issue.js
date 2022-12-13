frappe.ui.form.on("Issue", {
	onload: function(frm) {
		frm.email_field = "raised_by";
		frm.events.setup_queries(frm);
	},

	refresh: function (frm) {
		erpnext.hide_company();
		frm.events.set_dynamic_fields(frm);
		frm.events.setup_buttons(frm);
		frm.events.setup_dashboard(frm);
	},

	setup_queries: function (frm) {
		frm.set_query('contact_person', () => {
			if (frm.doc.customer) {
				frappe.dynamic_link = {
					doc: frm.doc,
					fieldname: 'customer',
					doctype: 'Customer'
				};
				return erpnext.queries.contact_query(frm.doc);
			}
		});

		frm.events.set_service_level_agreement_filters(frm);
	},

	setup_buttons: function (frm) {
		if (frm.doc.status !== "Closed" && frm.doc.agreement_fulfilled === "Ongoing") {
			if (frm.doc.status !== "In Progress") {
				frm.add_custom_button(__("In Progress"), function () {
					frm.set_value("status", "In Progress").then(() => frm.save());
				}, __("Status"));
			}

			if (frm.doc.status !== "To Update") {
				frm.add_custom_button(__("To Update"), function () {
					frm.set_value("status", "To Update").then(() => frm.save());
				}, __("Status"));
			}

			if (frm.doc.status !== "To Update") {
				frm.add_custom_button(__("On Hold"), function () {
					frm.set_value("status", "On Hold").then(() => frm.save());
				}, __("Status"));
			}

			frm.add_custom_button(__("Close"), function () {
				frm.set_value("status", "Closed").then(() => frm.save());
			}, __("Status"));

			frm.add_custom_button(__("Task"), function () {
				frappe.model.open_mapped_doc({
					method: "erpnext.support.doctype.issue.issue.make_task",
					frm: frm
				});
			}, __("Create"));
		} else {
			frm.add_custom_button(__("Reopen"), function () {
				frm.set_value("status", "Open").then(() => frm.save());
			}, __("Status"));
		}
	},

	setup_dashboard: function (frm) {
		if (frm.doc.service_level_agreement) {
			if (frm.doc.status !== "Closed" && frm.doc.agreement_fulfilled === "Ongoing") {
				frm.events.set_time_to_resolve_and_response(frm);
			} else {
				frm.events.set_agreement_fulfilment_dashboard(frm);
			}
		}
	},

	set_dynamic_fields: function (frm) {
		if (!frm.doc.__onload || !frm.doc.__onload.allow_resetting_service_level_agreement) {
			frm.set_df_property("reset_service_level_agreement", "hidden", 1);
		}
	},

	contact_person: function(frm) {
		erpnext.utils.get_contact_details(frm);
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
					indicator: 'green',
					message: __('Resetting Service Level Agreement.')
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

	set_service_level_agreement_filters: function (frm) {
		if (frm.doc.service_level_agreement) {
			frappe.call({
				method: "erpnext.support.doctype.service_level_agreement.service_level_agreement.get_service_level_agreement_filters",
				args: {
					name: frm.doc.service_level_agreement,
					customer: frm.doc.customer
				},
				callback: function (r) {
					if (r && r.message) {
						frm.set_query('priority', function () {
							return {
								filters: {
									"name": ["in", r.message.priority],
								}
							};
						});
						frm.set_query('service_level_agreement', function () {
							return {
								filters: {
									"name": ["in", r.message.service_level_agreements],
								}
							};
						});
					}
				}
			});
		} else {
			frm.fields_dict.priority.get_query = null;
			frm.fields_dict.service_level_agreement.get_query = null;
		}
	},

	set_time_to_resolve_and_response: function (frm) {
		frm.dashboard.clear_headline();

		var time_to_respond = frm.events.get_status(frm.doc.response_by_variance);
		if (!frm.doc.first_responded_on && frm.doc.agreement_fulfilled === "Ongoing") {
			time_to_respond = frm.events.get_time_left(frm.doc.response_by, frm.doc.agreement_fulfilled);
		}

		var time_to_resolve = frm.events.get_status(frm.doc.resolution_by_variance);
		if (!frm.doc.resolution_date && frm.doc.agreement_fulfilled === "Ongoing") {
			time_to_resolve = frm.events.get_time_left(frm.doc.resolution_by, frm.doc.agreement_fulfilled);
		}

		frm.dashboard.set_headline_alert(
		'<div class="row">' +
				'<div class="col-xs-6">' +
					'<span class="indicator whitespace-nowrap '+ time_to_respond.indicator +'"><span class="hidden-xs">Time to Respond: '+ time_to_respond.diff_display +'</span></span> ' +
				'</div>' +
				'<div class="col-xs-6">' +
					'<span class="indicator whitespace-nowrap '+ time_to_resolve.indicator +'"><span class="hidden-xs">Time to Resolve: '+ time_to_resolve.diff_display +'</span></span> ' +
				'</div>' +
			'</div>'
		);
	},

	set_agreement_fulfilment_dashboard: function (frm) {
		frm.dashboard.clear_headline();

		let agreement_fulfilled = (frm.doc.agreement_fulfilled == "Fulfilled") ?
			{"indicator": "green", "msg": "Service Level Agreement has been fulfilled"} :
			{"indicator": "red", "msg": "Service Level Agreement Failed"};

		frm.dashboard.set_headline_alert(
			'<div class="row">' +
				'<div class="col-xs-12">' +
					'<span class="indicator whitespace-nowrap ' + agreement_fulfilled.indicator + '"><span class="hidden-xs">' + agreement_fulfilled.msg + '</span></span> ' +
				'</div>' +
			'</div>'
		);
	},

	get_time_left: function (timestamp, agreement_fulfilled) {
		const diff = moment(timestamp).diff(moment());
		const diff_display = diff >= 44500 ? moment.duration(diff).humanize() : "Failed";
		let indicator = (diff_display == 'Failed' && agreement_fulfilled != "Fulfilled") ? "red" : "green";
		return {"diff_display": diff_display, "indicator": indicator};
	},

	get_status: function (variance) {
		if (variance > 0) {
			return {"diff_display": "Fulfilled", "indicator": "green"};
		} else {
			return {"diff_display": "Failed", "indicator": "red"};
		}
	}
});
