// Published as `erpnext/lib` through the import_map hook; a stored Client Script imports it by name.
import { h } from "vue";

/** A chip in ERPNext's brand colour that prefixes `label` with `erpnext/lib:`; takes one prop, `label`. */
export const CompanyBadge = {
	props: { label: { type: String, required: true } },
	setup(props) {
		return () =>
			h(
				"div",
				{
					class: "rounded-1 bg-erpnext-brand px-2 py-1 text-base text-white",
					"data-erpnext-lib": "",
				},
				[h("span", { class: "font-medium" }, "erpnext/lib: "), props.label]
			);
	},
};
