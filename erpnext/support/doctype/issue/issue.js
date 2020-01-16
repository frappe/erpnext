frappe.ui.form.on("Issue", {
	onload: function(frm) {
		frm.email_field = "raised_by";

		frappe.db.get_value("Support Settings", {name: "Support Settings"}, "allow_resetting_service_level_agreement", (r) => {
			if (!r.allow_resetting_service_level_agreement) {
				frm.set_df_property("reset_service_level_agreement", "hidden", 1) ;
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
						frm.set_query('priority', function() {
							return {
								filters: {
									"name": ["in", r.message.priority],
								}
							};
						});
						frm.set_query('service_level_agreement', function() {
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

		if (frm.doc.status !== "Closed" && frm.doc.agreement_fulfilled === "Ongoing") {
			if (frm.doc.service_level_agreement) {
				set_time_to_resolve_and_response(frm);
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
			}, __("Make"));
		} else {
			if (frm.doc.service_level_agreement) {
				frm.dashboard.clear_headline();

				let agreement_fulfilled = (frm.doc.agreement_fulfilled == "Fulfilled") ?
					{"indicator": "green", "msg": "Service Level Agreement has been fulfilled"} :
					{"indicator": "red", "msg": "Service Level Agreement Failed"};

				frm.dashboard.set_headline_alert(
					'<div class="row">' +
						'<div class="col-xs-12">' +
							'<span class="indicator whitespace-nowrap '+ agreement_fulfilled.indicator +'"><span class="hidden-xs">'+ agreement_fulfilled.msg +'</span></span> ' +
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
		// create button for "Help Article"
		if(frappe.model.can_create('Help Article')) {
			// Removing Help Article button if exists to avoid multiple occurance
			frm.timeline.wrapper.find('.comment-header .asset-details .btn-add-to-kb').remove();
			$('<button class="btn btn-xs btn-link btn-add-to-kb text-muted hidden-xs pull-right">'+
				__('Help Article') + '</button>')
				.appendTo(frm.timeline.wrapper.find('.comment-header .asset-details:not([data-communication-type="Comment"])'))
				.on('click', function() {
					var content = $(this).parents('.timeline-item:first').find('.timeline-item-content').html();
					var doc = frappe.model.get_new_doc('Help Article');
					doc.title = frm.doc.subject;
					doc.content = content;
					frappe.set_route('Form', 'Help Article', doc.name);
				});
		}

		if (!frm.timeline.wrapper.find('.btn-split-issue').length) {
			let split_issue = __("Split Issue")
			$(`<button class="btn btn-xs btn-link btn-add-to-kb text-muted hidden-xs btn-split-issue pull-right" style="display:inline-block; margin-right: 15px">
				${split_issue}
			</button>`)
				.appendTo(frm.timeline.wrapper.find('.comment-header .asset-details:not([data-communication-type="Comment"])'))
			if (!frm.timeline.wrapper.data("split-issue-event-attached")){
				frm.timeline.wrapper.on('click', '.btn-split-issue', (e) => {
					var dialog = new frappe.ui.Dialog({
						title: __("Split Issue"),
						fields: [
							{fieldname: 'subject', fieldtype: 'Data', reqd:1, label: __('Subject'), description: __('All communications including and above this shall be moved into the new Issue')}
						],
						primary_action_label: __("Split"),
						primary_action: function() {
							frm.call("split_issue", {
								subject: dialog.fields_dict.subject.value,
								communication_id: e.currentTarget.closest(".timeline-item").getAttribute("data-name")
							}, (r) => {
								let url = window.location.href
								let arr = url.split("/");
								let result = arr[0] + "//" + arr[2]
								frappe.msgprint(`New issue created: <a href="${result}/desk#Form/Issue/${r.message}">${r.message}</a>`)
								frm.reload_doc();
								dialog.hide();
							});
						}
					});
					dialog.show()
				})
				frm.timeline.wrapper.data("split-issue-event-attached", true)
			}
		}
	},
});

function set_time_to_resolve_and_response(frm) {
	frm.dashboard.clear_headline();

	var time_to_respond = get_status(frm.doc.response_by_variance);
	if (!frm.doc.first_responded_on && frm.doc.agreement_fulfilled === "Ongoing") {
		time_to_respond = get_time_left(frm.doc.response_by, frm.doc.agreement_fulfilled);
	}

	var time_to_resolve = get_status(frm.doc.resolution_by_variance);
	if (!frm.doc.resolution_date && frm.doc.agreement_fulfilled === "Ongoing") {
		time_to_resolve = get_time_left(frm.doc.resolution_by, frm.doc.agreement_fulfilled);
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
}

function get_time_left(timestamp, agreement_fulfilled) {
	const diff = moment(timestamp).diff(moment());
	const diff_display = diff >= 44500 ? moment.duration(diff).humanize() : "Failed";
	let indicator = (diff_display == 'Failed' && agreement_fulfilled != "Fulfilled") ? "red" : "green";
	return {"diff_display": diff_display, "indicator": indicator};
}

function get_status(variance) {
	if (variance > 0) {
		return {"diff_display": "Fulfilled", "indicator": "green"};
	} else {
		return {"diff_display": "Failed", "indicator": "red"};
	}
}