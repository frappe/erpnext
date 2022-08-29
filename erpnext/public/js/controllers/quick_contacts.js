frappe.provide('erpnext.contacts');

erpnext.contacts.QuickContacts = frappe.ui.form.Controller.extend({
	onload: function () {
		this.setup_contact_no_fields();
	},
	contact_display_info :function(contact,contact_display, type) {
		var me = this;

		if (contact) {
			me.set_dynamic_link();
			return frappe.call({
				method: "frappe.contacts.doctype.contact.contact.get_contact_details",
				args: {
					contact: contact,
					get_contact_no_list: 1,
					link_doctype: frappe.dynamic_link.doctype,
					link_name: me.frm.doc[frappe.dynamic_link.fieldname]
				},
				callback: function (r) {
					if (r.message) {
						$.each(r.message || {}, function (k, v) {
							var key_item = `${type}${k}`
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
			me.frm.set_value(contact_display, "");
		}
	},

	contact_person: function() {
		this.contact_display_info(me.frm.doc.contact_person,"contact_display", "");
	},
	secondary_contact_person: function() {
		this.contact_display_info(me.frm.doc.secondary_contact_person,"secondary_contact_display", "secondary_");
	},

	contact_mobile_setter: function(field_name, has_secondary_contact) {
		if (this.add_new_contact_number(`${field_name}contact_mobile`, 'is_primary_mobile_no', field_name)) {
			return;
		}

		var tasks = [];

		var mobile_no = this.frm.doc[`${field_name}contact_mobile`];
		if (mobile_no) {
			var contacts = frappe.contacts.get_contacts_from_number(this.frm, mobile_no);
			if (contacts && contacts.length && !contacts.includes(this.frm.doc[`${field_name}contact_person`])) {
				tasks = [
					() => this.frm.doc[`${field_name}contact_person`] = contacts[0],
					() => this.frm.trigger(`${field_name}contact_person`),
					() => {
						this.frm.doc[`${field_name}contact_mobile`] = mobile_no;
						this.frm.refresh_field(`${field_name}contact_mobile`);
					},
				];
			}
		}
		if(has_secondary_contact){
			tasks.push(() => {
				if (this.frm.doc.contact_mobile_2 == this.frm.doc.contact_mobile) {
					this.frm.doc.contact_mobile_2 = '';
					this.frm.refresh_field('contact_mobile_2');
				}
			});
		}

		return frappe.run_serially(tasks);
	},

	contact_mobile: function () {
		this.contact_mobile_setter("", true);
	},

	secondary_contact_mobile: function () {
		this.contact_mobile_setter("secondary_", false);
	},


	contact_mobile_2: function () {
		this.add_new_contact_number('contact_mobile_2', 'is_primary_mobile_no');
	},

	contact_phone: function () {
		this.add_new_contact_number('contact_phone', 'is_primary_phone');
	},

	add_new_contact_number: function (number_field, number_type, field_name) {
		if (this.frm.doc[number_field] == __("[Add New Number]")) {
			this.set_dynamic_link();
			frappe.contacts.add_new_number_dialog(this.frm, number_field,
				`${field_name}contact_person`, `${field_name}contact_display`, number_type,
				(phone) => {
					return frappe.run_serially([
						() => this.get_all_contact_nos(),
						() => this.frm.set_value(number_field, phone)
					]);
				}
			);

			this.frm.doc[number_field] = "";
			this.frm.refresh_field(number_field);

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

