class CallPopup {
	constructor(call_log) {
		this.caller_number = call_log.from;
		this.call_log = call_log;
		this.setup_listener();
		this.make();
	}

	make() {
		this.dialog = new frappe.ui.Dialog({
			'static': true,
			'minimizable': true,
			'fields': [{
				'fieldname': 'caller_info',
				'fieldtype': 'HTML'
			}, {
				'fielname': 'last_interaction',
				'fieldtype': 'Section Break',
				'label': __('Activity'),
			}, {
				'fieldtype': 'Small Text',
				'label': __('Last Communication'),
				'fieldname': 'last_communication',
				'read_only': true,
				'default': `<i class="text-muted">${__('No communication found.')}<i>`
			}, {
				'fieldtype': 'Small Text',
				'label': __('Last Issue'),
				'fieldname': 'last_issue',
				'read_only': true,
				'default': `<i class="text-muted">${__('No issue raised by the customer.')}<i>`
			}, {
				'fieldtype': 'Column Break',
			}, {
				'fieldtype': 'Small Text',
				'label': __('Call Summary'),
				'fieldname': 'call_summary',
			}, {
				'fieldtype': 'Button',
				'label': __('Save'),
				'click': () => {
					const call_summary = this.dialog.get_value('call_summary');
					if (!call_summary) return;
					frappe.xcall('erpnext.crm.doctype.utils.add_call_summary', {
						'docname': this.call_log.id,
						'summary': call_summary,
					}).then(() => {
						this.close_modal();
						frappe.show_alert({
							message: `${__('Call Summary Saved')}<br><a class="text-small text-muted" href="#Form/Call Log/${this.call_log.name}">${__('View call log')}</a>`,
							indicator: 'green'
						});
					});
				}
			}],
		});
		this.set_call_status();
		this.make_caller_info_section();
		this.dialog.get_close_btn().show();
		this.dialog.$body.addClass('call-popup');
		this.dialog.set_secondary_action(this.close_modal.bind(this));
		frappe.utils.play_sound('incoming-call');
		this.dialog.show();
	}

	make_caller_info_section() {
		const wrapper = this.dialog.get_field('caller_info').$wrapper;
		wrapper.append(`<div class="text-muted"> ${__("Loading...")} </div>`);
		frappe.xcall('erpnext.crm.doctype.utils.get_document_with_phone_number', {
			'number': this.caller_number
		}).then(contact_doc => {
			wrapper.empty();
			const contact = this.contact = contact_doc;
			if (!contact) {
				this.setup_unknown_caller(wrapper);
			} else {
				this.setup_known_caller(wrapper);
				this.set_call_status();
				this.make_last_interaction_section();
			}
		});
	}

	setup_unknown_caller(wrapper) {
		wrapper.append(`
			<div class="caller-info">
				<b>${__('Unknown Number')}:</b> ${this.caller_number}
				<button
					class="margin-left btn btn-new btn-default btn-xs"
					data-doctype="Contact"
					title=${__("Make New Contact")}>
					<i class="octicon octicon-plus text-medium"></i>
				</button>
			</div>
		`).find('button').click(
			() => frappe.set_route(`Form/Contact/New Contact?phone=${this.caller_number}`)
		);
	}

	setup_known_caller(wrapper) {
		const contact = this.contact;
		const contact_name = frappe.utils.get_form_link(contact.doctype, contact.name, true, this.get_caller_name());
		const links = contact.links ? contact.links : [];

		let contact_links = '';

		links.forEach(link => {
			contact_links += `<div>${link.link_doctype}: ${frappe.utils.get_form_link(link.link_doctype, link.link_name, true)}</div>`;
		});
		wrapper.append(`
			<div class="caller-info flex">
				${frappe.avatar(null, 'avatar-xl', contact.name, contact.image || '')}
				<div>
					<h5>${contact_name}</h5>
					<div>${contact.mobile_no || ''}</div>
					<div>${contact.phone_no || ''}</div>
					${contact_links}
				</div>
			</div>
		`);
	}

	set_indicator(color, blink=false) {
		let classes = `indicator ${color} ${blink ? 'blink': ''}`;
		this.dialog.header.find('.indicator').attr('class', classes);
	}

	set_call_status(call_status) {
		let title = '';
		call_status = call_status || this.call_log.status;
		if (['Ringing'].includes(call_status) || !call_status) {
			title = __('Incoming call from {0}', [this.get_caller_name()]);
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
		}, 10000);
	}

	make_last_interaction_section() {
		frappe.xcall('erpnext.crm.doctype.utils.get_last_interaction', {
			'number': this.caller_number,
			'reference_doc': this.contact
		}).then(data => {
			const comm_field = this.dialog.get_field('last_communication');
			if (data.last_communication) {
				const comm = data.last_communication;
				comm_field.set_value(comm.content);
			}

			if (data.last_issue) {
				const issue = data.last_issue;
				const issue_field = this.dialog.get_field("last_issue");
				issue_field.set_value(issue.subject);
				issue_field.$wrapper.append(`<a class="text-medium" href="#List/Issue?customer=${issue.customer}">
					${__('View all issues from {0}', [issue.customer])}
				</a>`);
			}
		});
	}
	get_caller_name() {
		return this.contact ? this.contact.lead_name || this.contact.name || '' : this.caller_number;
	}
	setup_listener() {
		frappe.realtime.on(`call_${this.call_log.id}_disconnected`, call_log => {
			this.call_disconnected(call_log);
			// Remove call disconnect listener after the call is disconnected
			frappe.realtime.off(`call_${this.call_log.id}_disconnected`);
		});
	}
}

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
