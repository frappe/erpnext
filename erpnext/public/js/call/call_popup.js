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
		this.set_call_status();
		frappe.utils.bind_actions_with_object(this.dialog.$body, this);
		this.dialog.$wrapper.addClass('call-popup');
		this.dialog.set_secondary_action(this.close_modal.bind(this));
		this.dialog.show();
	}

	setup_dialog() {
		if (this.is_known_caller()) {
			this.dialog.$body.html(frappe.render_template('call_popup', {
				'sidebar_items': [
					{'label': __('Call Details'), 'type': 'details', 'active': 1},
					{'label': __('Issues'), 'type': 'issue_list'},
					{'label': __('Calls'), 'type': 'previous_calls'},
				]
			}));
			this.setup_caller_activities();
		} else {
			this.dialog.$body.html(`<div class="details"></div>`);
		}
		this.setup_call_details();
		this.set_details(this.caller_info);
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
		} else if (call_status === 'No Answer') {
			this.set_indicator('red');
			title = __('Call Missed');
		} else if (['Completed', 'Busy'].includes(call_status)) {
			this.set_indicator('red');
			title = __('Call Ended');
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

	call_ended(call_log) {
		frappe.utils.play_sound('call-disconnect');
		this.update_call_log(call_log);
		setTimeout(() => {
			if (!this.dialog.get_value('call_summary')) {
				this.close_modal();
			}
		}, 30000);
	}

	get_caller_name() {
		const contact_link = this.get_contact_link();
		return contact_link.link_title || contact_link.link_name;
	}

	get_contact_link() {
		let log = this.call_log;
		let contact_link = log.links.find(d => d.link_doctype === 'Contact');
		return contact_link || {};
	}

	setup_listener() {
		frappe.realtime.on(`call_${this.call_log.id}_ended`, call_log => {
			this.call_ended(call_log);
			// Remove call disconnect listener after the call is disconnected
			frappe.realtime.off(`call_${this.call_log.id}_ended`);
		});
	}

	on_sidebar_item_click(e, $el) {
		let type = decodeURIComponent($el.data('type'));
		this.dialog.$body.find('.sidebar-item').removeClass('active');
		this.dialog.$body.find('.sidebar-item i').addClass('hide');
		$el.addClass('active');
		$el.find('i').removeClass('hide');
		if (type == 'details') {
			this.set_details(this.caller_info);
		} else if (type == 'issue_list') {
			this.set_details(this.issue_list);
		} else if (type == 'previous_calls') {
			this.set_details(this.previous_calls);
		}
	}

	setup_call_details() {
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
				'click': () => frappe.set_route('Form', 'Contact', this.get_contact_link().link_name),
				'depends_on': () => this.get_caller_name()
			}, {
				'fieldtype': 'Button',
				'label': __('Create New Contact'),
				'click': () => frappe.new_doc('Contact', { 'mobile_no': this.caller_number }),
				'depends_on': () => !this.get_caller_name()
			}, {
				'fieldtype': 'Button',
				'label': __('Create New Customer'),
				'click': this.create_new_customer(),
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
				'hide_border': 1,
			}, {
				'fieldtype': 'Small Text',
				'label': __('Call Summary'),
				'fieldname': 'call_summary',
			}, {
				'fieldtype': 'Button',
				'label': __('Save'),
				'click': () => {
					const call_summary = this.call_details.get_value('call_summary');
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
		frappe.xcall('erpnext.communication.doctype.call_log.call_log.get_caller_activities', {
			'number': this.caller_number
		}).then(activities => {
			this.setup_issues_list(activities.issues);
			this.setup_previous_calls(activities.previous_calls);
		});
	}

	setup_issues_list(issues) {
		this.issue_list = $(`<div>`);
		let list_html = '';
		issues.forEach(issue => {
			list_html += `<div class="list-item flex justify-between padding">
				<div>
					<a href="${frappe.utils.get_form_link('Issue', issue.name)}">
						${frappe.ellipsis(issue.subject, 55)}
					</a>
					<div class="text-muted">${issue.name}</div>
				</div>
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
		this.issue_list.html(html);
		this.dialog.$body.find('.sidebar-item[data-type="issue_list"] span.badge').text(issues.length);
		frappe.ui.form.make_control({
			df: {
				label: 'Link Other Issue',
				fieldtype: 'Link',
				fieldname: 'issue',
				options: 'Issue',
			},
			render_input: true,
			only_input: false,
			parent: this.issue_list.find('.search'),
		});
	}

	setup_previous_calls(previous_calls) {
		this.previous_calls = $(`<div>`);
		let list_html = '';
		previous_calls.forEach(call => {
			list_html += `<div class="list-item flex justify-between padding">
				<div>
					<a href="${frappe.utils.get_form_link('Call Log', call.name)}">
						${call.type} call from ${call.from} to ${call.to}
					</a>
					<div class="text-muted">
						${frappe.ellipsis(call.summary, 30) || __('No Summary')}
					</div>
				</div>
			</div>`;
		});
		let html = `
			<div>
				<div class="search"></div>
				<label>Previous Calls</label>
				<div class="list-items">
					${list_html}
				</div>
			</div>
		`;
		this.previous_calls.html(html);
		this.dialog.$body.find('.sidebar-item[data-type="previous_calls"] span.badge').text(previous_calls.length);
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
				$el.replaceWith(`<span>${__('Linked')}</span>`);
			});
		});
	}

	is_known_caller() {
		return Boolean(this.get_caller_name());
	}

	create_new_customer() {
		frappe.get_doc('Customer', { 'mobile_no': this.caller_number });
	}
}

window.CallPopup = CallPopup;

$(document).on('app_ready', function () {
	frappe.realtime.on('show_call_popup', call_log => {
		if (erpnext.call_popup && erpnext.call_popup.call_log.id === call_log.id) {
			erpnext.call_popup.update_call_log(call_log);
			erpnext.call_popup.dialog.show();
		} else {
			erpnext.call_popup = new CallPopup(call_log);
		}
	});
});
