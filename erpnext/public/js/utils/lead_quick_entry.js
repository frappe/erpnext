frappe.provide('frappe.ui.form');

frappe.ui.form.LeadQuickEntryForm = frappe.ui.form.QuickEntryForm.extend({
	init: function(doctype, after_insert) {
		this.skip_redirect_on_error = true;
		this._super(doctype, after_insert);
	},

	render_dialog: function() {
		this.mandatory = this.mandatory.concat(this.get_lead_fields());
		this.mandatory = this.mandatory.filter(d => d.fieldname != 'status');
		this._super();
		this.init_post_render_dialog_operations();
		this.set_sales_person_from_user();
	},

	init_post_render_dialog_operations: function () {
		var me = this;

		me.dialog.fields_dict["tax_id"].df.onchange = () => {
			var value = me.dialog.get_value('tax_id');
			value = erpnext.utils.get_formatted_ntn(value);
			me.dialog.doc.tax_id = value;
			me.dialog.get_field('tax_id').refresh();
			erpnext.utils.validate_duplicate_tax_id(me.dialog.doc, "tax_id");
		};

		me.dialog.fields_dict["tax_cnic"].df.onchange = () => {
			var value = me.dialog.get_value('tax_cnic');
			value = erpnext.utils.get_formatted_cnic(value);
			me.dialog.doc.tax_cnic = value;
			me.dialog.get_field('tax_cnic').refresh();
		};

		me.dialog.fields_dict["tax_strn"].df.onchange = () => {
			var value = me.dialog.get_value('tax_strn');
			value = erpnext.utils.get_formatted_strn(value);
			me.dialog.doc.tax_strn = value;
			me.dialog.get_field('tax_strn').refresh();
		};

		me.dialog.fields_dict["mobile_no"].df.onchange = () => {
			var value = me.dialog.get_value('mobile_no');
			value = erpnext.utils.get_formatted_mobile_pakistan(value);
			me.dialog.doc.mobile_no = value;
			me.dialog.get_field('mobile_no').refresh();
		};

		me.dialog.fields_dict["mobile_no_2"].df.onchange = () => {
			var value = me.dialog.get_value('mobile_no_2');
			value = erpnext.utils.get_formatted_mobile_pakistan(value);
			me.dialog.doc.mobile_no_2 = value;
			me.dialog.get_field('mobile_no_2').refresh();
		};
	},

	set_sales_person_from_user: function() {
		var me = this;
		if (!me.dialog.get_field('sales_person') || me.dialog.doc.sales_person || !me.dialog.doc.__islocal) {
			return;
		}

		erpnext.utils.get_sales_person_from_user(sales_person => {
			if (sales_person) {
				me.dialog.doc.sales_person = sales_person;
				me.dialog.get_field('sales_person').refresh();
			}
		});
	},

	get_lead_fields: function() {
		return [
			{
				fieldtype: "Section Break",
				label: __("Source"),
			},
			{
				label: __("Lead Source"),
				fieldname: "source",
				fieldtype: "Link",
				options: "Lead Source"
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Territory"),
				fieldname: "territory",
				fieldtype: "Link",
				options: "Territory"
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Sales Person"),
				fieldname: "sales_person",
				fieldtype: "Link",
				options: "Sales Person"
			},
			{
				fieldtype: "Section Break",
				label: __("Contact Details"),
			},
			{
				label: __("Mobile Number (Primary)"),
				fieldname: "mobile_no",
				fieldtype: "Data"
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Mobile Number (Secondary"),
				fieldname: "mobile_no_2",
				fieldtype: "Data"
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Phone Number"),
				fieldname: "phone_no",
				fieldtype: "Data"
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Email Id"),
				fieldname: "email_id",
				fieldtype: "Data"
			},

			{
				fieldtype: "Section Break",
				label: __("Address Details"),
			},
			{
				label: __("Address Line 1"),
				fieldname: "address_line1",
				fieldtype: "Data"
			},
			{
				label: __("Address Line 2"),
				fieldname: "address_line2",
				fieldtype: "Data"
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("City"),
				fieldname: "city",
				fieldtype: "Data"
			},
			{
				label: __("State"),
				fieldname: "state",
				fieldtype: "Data"
			},
			{
				label: __("Country"),
				fieldname: "country",
				fieldtype: "Link",
				options: "Country"
			},

			{
				fieldtype: "Section Break",
				label: __("Identification & Tax Id"),
			},
			{
				label: __("CNIC"),
				fieldname: "tax_cnic",
				fieldtype: "Data"
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Tax Id"),
				fieldname: "tax_id",
				fieldtype: "Data"
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("STRN"),
				fieldname: "tax_strn",
				fieldtype: "Data"
			},
		];
	},
})