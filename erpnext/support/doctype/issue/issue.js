frappe.ui.form.on("Issue", {
	onload: function (frm) {
		frm.email_field = "raised_by";

		frappe.db.get_value(
			"Support Settings",
			{ name: "Support Settings" },
			["allow_resetting_service_level_agreement", "track_service_level_agreement"],
			(r) => {
				if (r && r.track_service_level_agreement == "0") {
					frm.set_df_property("service_level_section", "hidden", 1);
				}
				if (r && r.allow_resetting_service_level_agreement == "0") {
					frm.set_df_property("reset_service_level_agreement", "hidden", 1);
				}
			}
		);

		// buttons
		if (frm.doc.status !== "Closed") {
			frm.add_custom_button(__("Close"), function () {
				frm.set_value("status", "Closed");
				frm.save();
			});

			frm.add_custom_button(
				__("Task"),
				function () {
					frappe.model.open_mapped_doc({
						method: "erpnext.support.doctype.issue.issue.make_task",
						frm: frm,
					});
				},
				__("Create")
			);
		} else {
			frm.add_custom_button(__("Reopen"), function () {
				frm.set_value("status", "Open");
				frm.save();
			});
		}
	},

	reset_service_level_agreement: function (frm) {
		let reset_sla = new frappe.ui.Dialog({
			title: __("Reset Service Level Agreement"),
			fields: [
				{
					fieldtype: "Data",
					fieldname: "reason",
					label: __("Reason"),
					reqd: 1,
				},
			],
			primary_action_label: __("Reset"),
			primary_action: (values) => {
				reset_sla.disable_primary_action();
				reset_sla.hide();
				reset_sla.clear();

				frappe.show_alert({
					indicator: "green",
					message: __("Resetting Service Level Agreement."),
				});

				frappe.call(
					"erpnext.support.doctype.service_level_agreement.service_level_agreement.reset_service_level_agreement",
					{
						reason: values.reason,
						user: frappe.session.user_email,
						doctype: frm.doc.doctype,
						docname: frm.doc.name,
					},
					() => {
						reset_sla.enable_primary_action();
						frm.refresh();
						frappe.msgprint(__("Service Level Agreement was reset."));
					}
				);
			},
		});

		reset_sla.show();
	},

	timeline_refresh: function (frm) {
		if (!frm.timeline.wrapper.find(".btn-split-issue").length) {
			let split_issue_btn = $(`
				<a class="action-btn btn-split-issue" title="${__("Split Issue")}">
					${frappe.utils.icon("branch", "sm")}
				</a>
			`);

			let communication_box = frm.timeline.wrapper.find('.timeline-item[data-doctype="Communication"]');
			communication_box.find(".actions").prepend(split_issue_btn);

			if (!frm.timeline.wrapper.data("split-issue-event-attached")) {
				frm.timeline.wrapper.on("click", ".btn-split-issue", (e) => {
					var dialog = new frappe.ui.Dialog({
						title: __("Split Issue"),
						fields: [
							{
								fieldname: "subject",
								fieldtype: "Data",
								reqd: 1,
								label: __("Subject"),
								description: __(
									"All communications including and above this shall be moved into the new Issue"
								),
							},
						],
						primary_action_label: __("Split"),
						primary_action: () => {
							frm.call(
								"split_issue",
								{
									subject: dialog.fields_dict.subject.value,
									communication_id: e.currentTarget
										.closest(".timeline-item")
										.getAttribute("data-name"),
								},
								(r) => {
									frappe.msgprint(
										`New issue created: <a href="/app/issue/${r.message}">${r.message}</a>`
									);
									frm.reload_doc();
									dialog.hide();
								}
							);
						},
					});
					dialog.show();
				});
				frm.timeline.wrapper.data("split-issue-event-attached", true);
			}
		}

		// create button for "Help Article"
		// if (frappe.model.can_create("Help Article")) {
		// 	// Removing Help Article button if exists to avoid multiple occurrence
		// 	frm.timeline.wrapper.find('.action-btn .btn-add-to-kb').remove();

		// 	let help_article = $(`
		// 		<a class="action-btn btn-add-to-kb" title="${__('Help Article')}">
		// 			${frappe.utils.icon('solid-info', 'sm')}
		// 		</a>
		// 	`);

		// 	let communication_box = frm.timeline.wrapper.find('.timeline-item[data-doctype="Communication"]');
		// 	communication_box.find('.actions').prepend(help_article);
		// 	if (!frm.timeline.wrapper.data("help-article-event-attached")) {
		// 		frm.timeline.wrapper.on('click', '.btn-add-to-kb', function () {
		// 			const content = $(this).parents('.timeline-item[data-doctype="Communication"]:first').find(".content").html();
		// 			const doc = frappe.model.get_new_doc("Help Article");
		// 			doc.title = frm.doc.subject;
		// 			doc.content = content;
		// 			frappe.set_route("Form", "Help Article", doc.name);
		// 		});
		// 	}
		// 	frm.timeline.wrapper.data("help-article-event-attached", true);
		// }
	},
});
