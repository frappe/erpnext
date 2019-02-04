frappe.ui.form.on('Chart of Accounts Importer', {
	onload: function (frm) {
		frm.set_value("company", "");
		frm.set_value("import_file", "");
	},
	refresh: function (frm) {
		// disable default save
		frm.disable_save();

		// make company mandatory
		frm.set_df_property('company', 'reqd', frm.doc.company ? 0 : 1);
		frm.set_df_property('import_file_section', 'hidden', frm.doc.company ? 0 : 1);
		frm.set_df_property('chart_preview', 'hidden',
			$(frm.fields_dict['chart_tree'].wrapper).html()!="" ? 0 : 1);

		// Show import button when file is successfully attached
		if (frm.doc.import_file) {
			frm.page.set_primary_action(__("Start Import"), function () {
				frappe.call({
					method: "erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.import_coa",
					args: {
						file_name: frm.doc.import_file,
						company: frm.doc.company
					},
					callback: function(r) { }
				});
			}).addClass('btn btn-primary');
		}

		// show download template button when company is properly selected
		if(frm.doc.company) {
			// download the csv template file
			frm.add_custom_button(__("Download template"), function () {
				let get_template_url = 'erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.download_template';
				open_url_post(frappe.request.url, { cmd: get_template_url, doctype: frm.doc.doctype });
			});
		} else {
			frm.set_value("import_file", "");
		}
	},

	import_file: function (frm) {
		if (!frm.doc.import_file) {
			$(frm.fields_dict['chart_tree'].wrapper).empty(); // empty wrapper on removing file
		} else {
			let parent = __('All Accounts');
			$(frm.fields_dict['chart_tree'].wrapper).empty(); // empty wrapper to load new data

			// generate tree structure based on the csv data
			new frappe.ui.Tree({
				parent: $(frm.fields_dict['chart_tree'].wrapper),
				label: parent,
				expandable: true,
				method: 'erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.get_coa',
				args: {
					file_name: frm.doc.import_file,
					parent: parent,
					doctype: 'Chart of Accounts Importer'
				},
				onclick: function(node) {
					parent = node.value;
				}
			});
		}
	},

	company: function (frm) {
		// validate that no Gl Entry record for the company exists.
		frappe.call({
			method: "erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.validate_company",
			args: {
				company: frm.doc.company
			},
			callback: function(r) {
				if(r.message==false) {
					frm.set_value("company", "");
					frappe.throw(__("Transactions against the company already exist! "))
				} else {
					frm.trigger("refresh");
				}
			}
		});
	}
});