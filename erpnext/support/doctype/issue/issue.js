frappe.ui.form.on("Issue", {
	onload: function(frm) {
		frm.email_field = "raised_by";
	},

	refresh: function(frm) {
		if(frm.doc.status!=="Closed") {
			frm.add_custom_button(__("Close"), function() {
				frm.set_value("status", "Closed");
				frm.save();
			});
		} else {
			frm.add_custom_button(__("Reopen"), function() {
				frm.set_value("status", "Open");
				frm.save();
			});
		}
		if (frm.doc.service_contract_status == 'Ongoing') {
				frm.trigger("make_dashboard");
		}
	},

	make_dashboard: function(frm) {
		
		frm.dashboard.refresh();
		const timer = `
			<div class="stopwatch" style="font-weight:bold">
				<span class="hours">00</span>
				<span class="colon">:</span>
				<span class="minutes">00</span>
				<span class="colon">:</span>
				<span class="seconds">00</span>
			</div>`;

		var section = frm.dashboard.add_section(timer);

		if (frm.doc.actual_start_date) {
			let currentIncrement = moment(frappe.datetime.now_datetime()).diff(moment(frm.doc.actual_start_date),"seconds");
			initialiseTimer();

			function initialiseTimer() {
				const interval = setInterval(function() {
					var current = setCurrentIncrement();
					updateStopwatch(current);
				}, 1000);
			}

			function updateStopwatch(increment) {
				var hours = Math.floor(increment / 3600);
				var minutes = Math.floor((increment - (hours * 3600)) / 60);
				var seconds = increment - (hours * 3600) - (minutes * 60);

				$(section).find(".hours").text(hours < 10 ? ("0" + hours.toString()) : hours.toString());
				$(section).find(".minutes").text(minutes < 10 ? ("0" + minutes.toString()) : minutes.toString());
				$(section).find(".seconds").text(seconds < 10 ? ("0" + seconds.toString()) : seconds.toString());
			}

			function setCurrentIncrement() {
				currentIncrement += 1;
				return currentIncrement;
			}
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
	}
});
