class CallPopup {
	constructor(call_log) {
		this.caller_number = call_log.from;
		this.call_log = call_log;
		this.setup_listener();
		this.make();
	}

	make() {
		frappe.utils.play_sound('incoming-call');
		this.dialog = new frappe.ui.Dialog({
			'static': true,
			'minimizable': true
		});
		this.dialog.get_close_btn().show();
		this.setup_dialog();
		this.setup_additional_info();
		this.setup_caller_activities();
		this.set_call_status();
		frappe.utils.bind_actions_with_object(this.dialog.$body, this);
		this.dialog.$wrapper.addClass('call-popup');
		this.dialog.set_secondary_action(this.close_modal.bind(this));
		this.dialog.show();
		// show call details by default
		this.dialog.$body.find('.sidebar-item[data-type="name"]').click();
	}

	set_indicator(color, blink=false) {
		let classes = `indicator ${color} ${blink ? 'blink': ''}`;
		this.dialog.header.find('.indicator').attr('class', classes);
	}

	set_call_status(call_status) {
		let title = '';
		call_status = call_status || this.call_log.status;
		if (['Ringing'].includes(call_status) || !call_status) {
			title = __('Incoming call from {0}', [this.get_caller_name() || this.caller_number]);
			this.set_indicator('blue', true);
		} else if (call_status === 'In Progress') {
			title = __('Call Connected');
			this.set_indicator('yellow');
		} else if (call_status === 'Missed') {
			this.set_indicator('red');
			title = __('Call Missed');
		} else if (['Completed', 'Disconnected'].includes(call_status)) {
			this.set_indicator('red');
			title = __('Call Disconnected');
		} else {
			this.set_indicator('blue');
			title = call_status;
		}
		this.dialog.set_title(title);
	}

	update_call_log(call_log) {
		this.call_log = call_log;
		this.set_call_status();
	}

	close_modal() {
		this.dialog.hide();
		delete erpnext.call_popup;
	}

	call_disconnected(call_log) {
		frappe.utils.play_sound('call-disconnect');
		this.update_call_log(call_log);
		setTimeout(() => {
			if (!this.dialog.get_value('call_summary')) {
				this.close_modal();
			}
		}, 30000);
	}

	get_caller_name() {
		let log = this.call_log;
		const caller_name = log.links.filter(d => d.link_doctype === 'Contact').link_title;
		return caller_name;
	}

	setup_listener() {
		frappe.realtime.on(`call_${this.call_log.id}_disconnected`, call_log => {
			this.call_disconnected(call_log);
			// Remove call disconnect listener after the call is disconnected
			frappe.realtime.off(`call_${this.call_log.id}_disconnected`);
		});
	}

	setup_dialog() {
		this.dialog.$body.html(frappe.render_template('call_popup', {
			'sidebar_items': [
				{'label': 'Call Details', 'type': 'name'},
				{'label': 'Issue', 'type': 'data'}
			]
		}));
	}

	on_sidebar_item_click(e, $el) {
		let type = decodeURIComponent($el.data('type'));
		this.dialog.$body.find('.sidebar-item').removeClass('active');
		$el.addClass('active');
		if (type == 'name') {
			this.set_details(this.caller_info);
		} else {
			this.set_details(this.caller_activities);
		}
	}

	setup_additional_info() {
		this.caller_info = $(`<div></div>`);
		this.call_details = new frappe.ui.FieldGroup({
			fields: [{
				'fieldname': 'name',
				'label': 'Name',
				'default': this.get_caller_name() || __('Unknown Caller'),
				'fieldtype': 'Data',
				'read_only': 1
			}, {
				'fieldtype': 'Button',
				'label': __('Open Contact'),
				'click': () => frappe.set_route('Form', 'Contact', this.call_log.contact),
				'depends_on': () => this.call_log.contact
			}, {
				'fieldtype': 'Button',
				'label': __('Create New Contact'),
				'click': () => frappe.new_doc('Contact', { 'mobile_no': this.caller_number }),
				'depends_on': () => !this.get_caller_name()
			}, {
				'fieldtype': 'Button',
				'label': __('Create New Lead'),
				'click': () => frappe.new_doc('Lead', { 'mobile_no': this.caller_number }),
				'depends_on': () => !this.get_caller_name()
			}, {
				'fieldtype': 'Column Break',
			}, {
				'fieldname': 'number',
				'label': 'Phone Number',
				'fieldtype': 'Data',
				'default': this.caller_number,
				'read_only': 1
			}, {
				'fieldtype': 'Section Break',
			}, {
				'fieldtype': 'Small Text',
				'label': __('Call Summary'),
				'fieldname': 'call_summary',
			}, {
				'fieldtype': 'Button',
				'label': __('Save'),
				'click': () => {
					const call_summary = this.form.get_value('call_summary');
					if (!call_summary) return;
					frappe.xcall('erpnext.communication.doctype.call_log.call_log.add_call_summary', {
						'call_log': this.call_log.name,
						'summary': call_summary,
					}).then(() => {
						this.close_modal();
						frappe.show_alert({
							message: `
								${__('Call Summary Saved')}
								<br>
								<a
									class="text-small text-muted"
									href="#Form/Call Log/${this.call_log.name}">
									${__('View call log')}
								</a>
							`,
							indicator: 'green'
						});
					});
				}
			}],
			body: this.caller_info
		});
		this.call_details.make();
	}

	setup_caller_activities() {
		this.caller_activities = $(`<div></div>`);
		let list_html = '';
		frappe.xcall('erpnext.communication.doctype.call_log.call_log.get_caller_activities', {
			'number': this.caller_number
		}).then((act) => {
			act.issues.forEach(issue => {
				list_html += `<div class="list-item flex justify-between padding">
					<a class="issue-label" data-value="${issue.name}">${issue.name}</a>
					<a data-value="${issue.name}" data-action="link_issue">link</a>
				</div>`;
			});
			let html = `
				<div>
					<div class="search"></div>
					<label>Previous Issues</label>
					<div class="list-items">
						${list_html}
					</div>
				</div>
			`;
			this.caller_activities.html(html);
			this.dialog.$body.find('.sidebar-item[data-type="data"] > a > span.badge').text(act.issues.length);
			let search_input = frappe.ui.form.make_control({
				df: {
					label: 'Link Other Issue',
					fieldtype: 'Link',
					fieldname: 'issue',
					options: 'Issue',
				},
				render_input: 1,
				parent: this.caller_activities.find('.search'),
			});
		});
	}

	set_details(html) {
		this.dialog.$body.find('.details').empty();
		this.dialog.$body.find('.details').append(html);
	}

	link_issue(e, $el) {
		let issue_name = $el.data().value;
		frappe.confirm(__("Are you sure you want to link current call with issue: {0}", [issue_name.bold()]), () => {
			$el.unbind('click');
			frappe.xcall('erpnext.communication.doctype.call_log.call_log.link_issue', {
				'call_id': this.call_log.id,
				'issue': issue_name
			}).then(() => {
				$el.removeAttr('data-action');
				$el.replaceWith('<span>Linked</span>');
			});
		});
	}
}

window.CallPopup = CallPopup;

$(document).on('app_ready', function () {
	frappe.realtime.on('show_call_popup', call_log => {
		if (!erpnext.call_popup) {
			erpnext.call_popup = new CallPopup(call_log);
		} else {
			erpnext.call_popup.update_call_log(call_log);
			erpnext.call_popup.dialog.show();
		}
	});
});
