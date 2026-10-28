import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useCall } from "frappe-ui";

const COSTING = "/api/v2/method/erpnext.projects.doctype.project.costing.project_costing.get_project_costing";
const ACCOUNTS = "/api/v2/method/erpnext.projects.doctype.project.costing.accounts.get_project_accounts";

/**
 * The Costing tab's data, loaded once the tab is on screen.
 *
 * The form mounts the island as it loads, whichever tab is open, and hands it the Project on
 * every unsaved edit. The costing reads only saved documents, so it loads when `element` first
 * shows and again only after the Project is saved, which moves `modified`.
 */
export function useProjectCosting(element, project, modified) {
	return useOnScreenCall(element, COSTING, project, modified);
}

/**
 * The Accounts view's data, loaded once `active` turns true while the tab is on screen.
 *
 * Budget records are changed on their own forms, which leave the Project's `modified` as it was,
 * so the view loads again whenever the tab comes back on screen.
 */
export function useProjectAccounts(element, project, modified, active) {
	return useOnScreenCall(element, ACCOUNTS, project, modified, { active, reload_on_show: true });
}

/**
 * A GET of `url` for the project, sent when `element` is on screen and its key changed since the
 * last one: the project, its `modified` and, with `reload_on_show`, each time it comes back on
 * screen. A GET, as desk keeps its CSRF token where frappe-ui does not read it, and a read needs
 * none.
 */
function useOnScreenCall(
	element,
	url,
	project,
	modified,
	{ active = () => true, reload_on_show = false } = {}
) {
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
		const key = `${project()}|${modified()}|${reload_on_show ? shown.value : ""}`;
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
