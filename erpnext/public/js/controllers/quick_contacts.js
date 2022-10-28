frappe.provide('erpnext.contacts');

erpnext.contacts.QuickContacts = frappe.ui.form.Controller.extend({
	onload: function () {
		this.setup_contact_no_fields();
	},

	contact_person: function() {
		this.get_contact_details();
	},
	secondary_contact_person: function() {
		this.get_contact_details("secondary_");
	},

	get_contact_details: function(prefix) {
		var me = this;

		if (!prefix) {
			prefix = "";
		}
		var contact_fieldname = prefix + "contact_person";
		var display_fieldname = prefix + "contact_display";
		var contact = me.frm.doc[contact_fieldname];

		var lead = frappe.dynamic_link.doctype == "Lead" ? me.frm.doc[frappe.dynamic_link.fieldname] : null;

		if (contact || lead) {
			me.set_dynamic_link();
			return frappe.call({
				method: "erpnext.accounts.party.get_contact_details",
				args: {
					contact: contact || "",
					lead: lead,
					get_contact_no_list: 1,
					link_doctype: frappe.dynamic_link.doctype,
					link_name: me.frm.doc[frappe.dynamic_link.fieldname]
				},
				callback: function (r) {
					if (r.message) {
						$.each(r.message || {}, function (k, v) {
							var key_item = `${prefix}${k}`;
							if (me.frm.get_field(key_item)) {
								me.frm.doc[key_item] = v;
								me.frm.refresh_field(key_item);
							}
						});
						me.setup_contact_no_fields(r.message.contact_nos);
					}
				}
			});
		} else {
			me.frm.set_value(display_fieldname, "");
		}
	},

	contact_mobile: function () {
		this.get_contact_from_number();
	},

	secondary_contact_mobile: function () {
		this.get_contact_from_number("secondary_");
	},

	get_contact_from_number: function(prefix) {
		if (!prefix) {
			prefix = "";
		}
		var mobile_field = prefix + "contact_mobile";
		var contact_field = prefix + "contact_person";

		if (this.add_new_contact_number("contact_mobile", 'is_primary_mobile_no', prefix)) {
			return;
		}

		var tasks = [];

		var mobile_no = this.frm.doc[mobile_field];
		if (mobile_no) {
			var contacts = frappe.contacts.get_contacts_from_number(this.frm, mobile_no);
			if (contacts && contacts.length && !contacts.includes(this.frm.doc[contact_field])) {
				tasks = [
					() => this.frm.doc[contact_field] = contacts[0],
					() => this.frm.trigger(contact_field),
					() => {
						this.frm.doc[mobile_field] = mobile_no;
						this.frm.refresh_field(mobile_field);
					},
				];
			}
		}

		tasks.push(() => {
			if (this.frm.doc.contact_mobile_2 == this.frm.doc.contact_mobile) {
				this.frm.doc.contact_mobile_2 = '';
				this.frm.refresh_field('contact_mobile_2');
			}
		});

		return frappe.run_serially(tasks);
	},


	contact_mobile_2: function () {
		this.add_new_contact_number('contact_mobile_2', 'is_primary_mobile_no');
	},

	contact_phone: function () {
		this.add_new_contact_number('contact_phone', 'is_primary_phone');
	},

	add_new_contact_number: function (number_field, number_type, prefix) {
		if (!prefix) {
			prefix = "";
		}
		var mobile_field = prefix + number_field;
		var mobile_no = this.frm.doc[mobile_field];
		var contact_field = prefix + "contact_person";
		var display_field = prefix + "contact_display";

		if (mobile_no == __("[Add New Number]")) {
			this.set_dynamic_link();
			frappe.contacts.add_new_number_dialog(this.frm, mobile_field,
				contact_field, display_field, number_type,
				(phone) => {
					return frappe.run_serially([
						() => this.get_all_contact_nos(),
						() => this.frm.set_value(mobile_field, phone)
					]);
				}
			);

			this.frm.doc[mobile_field] = "";
			this.frm.refresh_field(mobile_field);

			return true;
		}
	},

	setup_contact_no_fields: function (contact_nos) {
		this.set_dynamic_link();

		if (contact_nos) {
			frappe.contacts.set_all_contact_nos(this.frm, contact_nos);
		}

		frappe.contacts.set_contact_no_select_options(this.frm, 'contact_mobile', 'is_primary_mobile_no', true);
		frappe.contacts.set_contact_no_select_options(this.frm, 'contact_mobile_2', 'is_primary_mobile_no', true);
		frappe.contacts.set_contact_no_select_options(this.frm, 'contact_phone', 'is_primary_phone', true);

		frappe.contacts.set_contact_no_select_options(this.frm, 'secondary_contact_mobile', 'is_primary_mobile_no', true);
	},

	get_all_contact_nos: function () {
		this.set_dynamic_link();
		return frappe.run_serially([
			() => frappe.contacts.get_all_contact_nos(this.frm, frappe.dynamic_link.doctype,
				this.frm.doc[frappe.dynamic_link.fieldname]),
			() => this.setup_contact_no_fields()
		]);
	},
});

