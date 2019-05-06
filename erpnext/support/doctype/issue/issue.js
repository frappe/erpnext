frappe.ui.form.on("Issue", {
	onload: function(frm) {
		frm.email_field = "raised_by";
	},

	refresh: function (frm) {
		if (frm.doc.service_level_agreement && frm.doc.status !== "Closed") {
			set_time_to_resolve_and_response(frm);
		}

		if (frm.doc.status !== "Closed") {
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
			frm.add_custom_button(__("Reopen"), function () {
				frm.set_value("status", "Open");
				frm.save();
			});
		}
	},

	priority: function(frm) {
		if (frm.doc.service_level_agreement) {
			frm.call('change_sla_priority', {
				"priority": frm.doc.priority
			}).then(() => {
				frm.refresh();
			});
		}
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

	var time_to_respond = get_time_left(frm.doc.response_by);
	var time_to_resolve = get_time_left(frm.doc.resolution_by);

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

function get_time_left(timestamp) {
	const diff = moment(timestamp).diff(moment());
	const diff_display = diff >= 44500 ? moment.duration(diff).humanize() : moment(0, 'seconds').format('HH:mm');
	var indicator = "green";
	if (diff_display == '00:00') {
		indicator = "red";
	}
	return {"diff_display": diff_display, "indicator": indicator};
}
