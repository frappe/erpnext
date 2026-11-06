import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useCall } from "frappe-ui";

const COSTING = "/api/v2/method/erpnext.projects.doctype.project.costing.project_costing.get_project_costing";
const ACCOUNTS = "/api/v2/method/erpnext.projects.doctype.project.costing.accounts.get_project_accounts";

/**
 * The Costing tab's data, loaded once the tab is on screen.
 *
 * The form mounts the island as it loads, whichever tab is open, and hands it the Project on
 * every unsaved edit. The costing reads only saved documents, so it loads when `element` shows and
 * after the Project is saved, not on every edit.
 */
export function useProjectCosting(element, project, modified) {
	return useOnScreenCall(element, COSTING, project, modified);
}

/** The Accounts view's data, loaded the same way once `active` turns true. */
export function useProjectAccounts(element, project, modified, active) {
	return useOnScreenCall(element, ACCOUNTS, project, modified, active);
}

/**
 * A GET of `url` for the project, sent each time `element` comes on screen and when the project
 * or its `modified` changes while it is. Timesheets, invoices and Budget records change on their
 * own forms and leave the Project's `modified` as it was, so coming back to the tab is what picks
 * them up; it also retries a load that failed. A GET, as desk keeps its CSRF token where frappe-ui
 * does not read it, and a read needs none.
 */
function useOnScreenCall(element, url, project, modified, active = () => true) {
	const visible = ref(false);
	const shown = ref(0);
	const call = useCall({
		url,
		method: "GET",
		immediate: false,
		params: () => ({ project: project() }),
	});

	let loaded_for = null;
	watch([visible, project, modified, active], () => {
		const key = `${project()}|${modified()}|${shown.value}`;
		if (!visible.value || !active() || !project() || key === loaded_for) return;
		loaded_for = key;
		call.reload();
	});

	let observer;
	onMounted(() => {
		observer = new IntersectionObserver(([entry]) => {
			if (entry.isIntersecting && !visible.value) shown.value++;
			visible.value = entry.isIntersecting;
		});
		observer.observe(element.value);
	});
	onBeforeUnmount(() => observer?.disconnect());

	return call;
}
