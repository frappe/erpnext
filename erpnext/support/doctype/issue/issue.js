frappe.ui.form.on("Issue", {
	onload: function(frm) {
		frm.email_field = "raised_by";

		frappe.db.get_value("Support Settings", {name: "Support Settings"},
			["allow_resetting_service_level_agreement", "track_service_level_agreement"], (r) => {
				if (r && r.track_service_level_agreement == "0") {
					frm.set_df_property("service_level_section", "hidden", 1);
				}
				if (r && r.allow_resetting_service_level_agreement == "0") {
					frm.set_df_property("reset_service_level_agreement", "hidden", 1);
				}
		});
	},

	refresh: function (frm) {
		if (frm.doc.status !== "Closed" && frm.doc.agreement_status === "Ongoing") {
			frm.add_custom_button(__("Task"), function () {
				frappe.model.open_mapped_doc({
					method: "erpnext.support.doctype.issue.issue.make_task",
					frm: frm
				});
			}, __("Create"));
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

				frappe.call("erpnext.support.doctype.service_level_agreement.service_level_agreement.reset_service_level_agreement", {
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