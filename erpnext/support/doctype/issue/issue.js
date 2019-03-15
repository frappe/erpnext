frappe.ui.form.on("Issue", {
	onload: function(frm) {
		frm.email_field = "raised_by";
		console.log("this.set_time_to_resolve_and_response()");
		this.set_time_to_resolve_and_response();
	},

	refresh: function (frm) {
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
	set_time_to_resolve_and_response: function(frm) {
		const customer = $('div[data-fieldname="customer"]');
		const email_account = $('div[data-fieldname="email_account"]');

		const time_to_respond = $(this.get_time_left_element(__('Time To Respond'), frm.doc.response_by));
		const time_to_resolve = $(this.get_time_left_element(__('Time To Resolve'), frm.doc.resolve_by));

		time_to_respond.insertAfter(customer);
		time_to_resolve.insertAfter(email_account);
	},
	get_time_left_element(label, timestamp) {
		return `
			<div class="frappe-control input-max-width">
			<div class="form-group">
				<div class="clearfix">
				<label class="control-label" style="padding-right: 0px;">
					${label}
				</label>
				</div>
				<div class="control-input-wrapper">
				<div class="control-value like-disabled-input">${this.get_time_left(timestamp)}</div>
				</div>
			</div>
			</div>
		`;
	},
	get_time_left(timestamp) {
		const diff = moment(timestamp).diff(moment());
		return diff >= 44500 ? moment.duration().humanize() : 0;
	}
});