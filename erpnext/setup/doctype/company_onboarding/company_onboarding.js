// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Company Onboarding", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.events.render(frm);
		// steps are checked against the company's data each time the form opens
		frm.call("check_steps").then((r) => r.message && frm.reload_doc());
	},

	render(frm) {
		const $wrapper = frm.get_field("onboarding_html").$wrapper.empty();
		// 16px above, between and below the cards: the tabs already leave 10px, pt-1.5 adds 6
		$wrapper.closest(".section-body").addClass("pt-0");
		const $page = $(`<div class="flex flex-col gap-4 pt-1.5 mb-4"></div>`).appendTo($wrapper);
		$page.append(make_company_card(frm));
		new CompanyOnboardingWidget({ container: $page, frm: frm });
	},
});

// Frappe's onboarding card from the Home page, fed with this company's steps
class CompanyOnboardingWidget extends frappe.widget.widget_factory.onboarding {
	async refresh() {
		this.steps = this.get_steps();
		this.set_title();
		this.set_actions();
		this.set_body();
		this.setup_events();
	}

	get_steps() {
		const details = this.frm.doc.__onload?.steps || {};
		return (this.frm.doc.steps || []).map((row) => ({
			key: row.step_key,
			title: details[row.step_key]?.title || row.step,
			description: details[row.step_key]?.description,
			is_complete: row.status === "Done",
			is_skipped: row.status === "Skipped",
		}));
	}

	set_title() {
		this.title_field.text(__("Set up {0}", [this.frm.doc.company]));
	}

	set_actions() {
		const live = this.frm.doc.status === "Live";
		this.action_area
			.empty()
			.append(frappe.ui.badge({ label: __(this.frm.doc.status), theme: live ? "green" : "blue" }));
	}

	is_dismissed() {
		return false;
	}

	capture_step_event() {}

	show_success() {
		if (this.$done) return;
		this.$done = $(`<div class="px-2 py-2 text-p-sm text-ink-gray-6"></div>`)
			.text(__("All steps are done or skipped."))
			.appendTo(this.body);
	}

	make_step_content(step) {
		const $body = $(`<div class="onboarding-step-content flex flex-col gap-3"></div>`);
		if (step.description) {
			$(`<div class="onboarding-step-description text-p-sm text-ink-gray-6"></div>`)
				.text(step.description)
				.appendTo($body);
		}

		const make_actions = STEP_ACTIONS[step.key.split(".").pop()];
		const buttons = step.is_skipped || !make_actions ? [] : make_actions(this.frm, step);
		if (step.is_skipped) {
			buttons.push({
				label: __("Do this step"),
				variant: "subtle",
				onclick: () => this.set_skipped(step, 0),
			});
		} else if (!step.is_complete) {
			buttons.push({
				label: __("Skip"),
				variant: "ghost",
				onclick: () => this.set_skipped(step, 1),
			});
		}
		if (buttons.length) {
			const $actions = $(`<div class="flex flex-wrap items-center gap-2"></div>`).appendTo($body);
			buttons.forEach((opts) => $actions.append(frappe.ui.button(opts)));
		}
		return $body;
	}

	set_skipped(step, skip) {
		return this.frm
			.call("skip_step", { step_key: step.key, skip: skip })
			.then(() => this.frm.reload_doc());
	}
}

// Buttons of each step, by the last part of its hook path
const STEP_ACTIONS = {
	chart_of_accounts: (frm, step) => {
		if (step.is_complete) {
			return [
				{
					label: __("Open Chart of Accounts"),
					icon_right: "arrow-up-right",
					onclick: () => {
						frappe.route_options = { company: frm.doc.company };
						frappe.set_route("Tree", "Account");
					},
				},
				{
					label: __("Change"),
					variant: "ghost",
					onclick: () => frm.call("change_chart_choice").then(() => frm.reload_doc()),
				},
			];
		}
		// two equal answers to one question, so neither looks like the main button
		return [
			{
				label: __("Use the existing chart"),
				icon: "list-tree",
				onclick: () => frm.call("use_existing_chart").then(() => frm.reload_doc()),
			},
			{ label: __("Import a sheet"), icon: "import", disabled: true, tooltip: __("Coming soon") },
			{ label: __("From Tally"), disabled: true, tooltip: __("Coming soon") },
		];
	},
	opening_balances: (frm, step) =>
		step.is_complete
			? []
			: [
					{
						label: __("Open opening balances"),
						variant: "solid",
						icon_right: "arrow-right",
						onclick: () => frm.scroll_to_field("opening_balances"),
					},
			  ],
};

function make_company_card(frm) {
	const details = frm.doc.__onload?.company_details || {};
	// white bordered card, the same contact-box style as the contact cards on Customer
	const $card = $(`<div class="contact-box flex flex-col gap-3 mb-0">
		<div class="flex items-center gap-3">
			<span class="company-logo shrink-0"></span>
			<div class="flex flex-col gap-1 min-w-0 grow">
				<div class="company-name text-base-semibold text-ink-gray-8 truncate"></div>
				<div class="company-meta text-sm text-ink-gray-5"></div>
			</div>
			<span class="company-edit shrink-0"></span>
		</div>
		${frappe.ui.divider.html()}
		<div class="company-lines grid gap-3" style="grid-template-columns: repeat(2, minmax(0, 1fr))"></div>
	</div>`);

	$card.find(".company-logo").html(
		frappe.ui.avatar.html({
			image: details.company_logo,
			label: details.company_name,
			size: "xl",
			shape: "square",
		})
	);
	$card.find(".company-name").text(details.company_name || frm.doc.company);
	$card
		.find(".company-meta")
		.text([details.abbr, details.country, details.default_currency].filter(Boolean).join(" · "));
	$card.find(".company-edit").append(
		frappe.ui.button({
			label: __("Edit"),
			icon: "pencil",
			onclick: () => edit_company_details(frm, details),
		})
	);

	const address = ["address_line1", "address_line2", "city", "state", "pincode", "country"]
		.map((field) => details[field])
		.filter(Boolean)
		.join(", ");
	const lines = [
		["receipt", __("Tax ID"), details.tax_id],
		["phone", __("Phone"), details.phone_no],
		["mail", __("Email"), details.email],
		["globe", __("Website"), details.website],
		["map-pin", __("Address"), details.address_line1 ? address : "", true],
	];
	const $lines = $card.find(".company-lines");
	for (const [icon, label, value, full_width] of lines) {
		const $line = $(`<div class="contact-line flex items-center gap-2 min-w-0"></div>`)
			.attr("title", label)
			.append(frappe.utils.icon(icon, "sm", "", "", "text-ink-gray-5 shrink-0", true))
			.appendTo($lines);
		// the address is the long one, so it takes the whole row
		if (full_width) $line.css("grid-column", "1 / -1");
		$("<span class='truncate'></span>")
			.addClass(value ? "text-ink-gray-7" : "text-ink-gray-4")
			.text(value || __("{0} not set", [label]))
			.appendTo($line);
	}
	return $card;
}

function edit_company_details(frm, details) {
	const dialog = new frappe.ui.Dialog({
		title: __("Company details"),
		fields: [
			{ fieldname: "company_logo", fieldtype: "Attach Image", label: __("Logo") },
			{ fieldname: "tax_id", fieldtype: "Data", label: __("Tax ID") },
			{ fieldtype: "Column Break" },
			{ fieldname: "phone_no", fieldtype: "Data", options: "Phone", label: __("Phone") },
			{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("Email") },
			{ fieldname: "website", fieldtype: "Data", options: "URL", label: __("Website") },
			{ fieldtype: "Section Break", label: __("Address") },
			{ fieldname: "address_line1", fieldtype: "Data", label: __("Address Line 1") },
			{ fieldname: "address_line2", fieldtype: "Data", label: __("Address Line 2") },
			{ fieldname: "city", fieldtype: "Data", label: __("City") },
			{ fieldtype: "Column Break" },
			{ fieldname: "state", fieldtype: "Data", label: __("State") },
			{ fieldname: "pincode", fieldtype: "Data", label: __("Postal Code") },
			{ fieldname: "country", fieldtype: "Link", options: "Country", label: __("Country") },
			{ fieldtype: "Section Break", label: __("More"), collapsible: 1 },
			{ fieldname: "date_of_incorporation", fieldtype: "Date", label: __("Date of Incorporation") },
			{
				fieldname: "registration_details",
				fieldtype: "Small Text",
				label: __("Registration Details"),
				description: __("For example PAN, CIN or MSME number."),
			},
		],
		primary_action_label: __("Save"),
		primary_action: (values) =>
			frm.call("update_company_details", { values: values }).then(() => {
				dialog.hide();
				frm.reload_doc();
			}),
	});
	dialog.set_values(details);
	dialog.show();
}
