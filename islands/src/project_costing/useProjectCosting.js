import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useCall } from "frappe-ui";

const METHOD = "/api/v2/method/erpnext.projects.doctype.project.costing.project_costing.get_project_costing";

/**
 * The Costing tab's data, loaded once the tab is on screen.
 *
 * The form mounts the island as it loads, whichever tab is open, and hands it the Project on
 * every unsaved edit. The costing reads only saved documents, so it loads when `element` first
 * shows and again only after the Project is saved, which moves `modified`.
 *
 * A GET, as desk keeps its CSRF token where frappe-ui does not read it, and a read needs none.
 */
export function useProjectCosting(element, project, modified) {
	const visible = ref(false);
	const costing = useCall({
		url: METHOD,
		method: "GET",
		immediate: false,
		params: () => ({ project: project() }),
	});

	let loaded_for = null;
	watch([visible, project, modified], () => {
		const key = `${project()}|${modified()}`;
		if (!visible.value || !project() || key === loaded_for) return;
		loaded_for = key;
		costing.reload();
	});

	let observer;
	onMounted(() => {
		observer = new IntersectionObserver(([entry]) => (visible.value = entry.isIntersecting));
		observer.observe(element.value);
	});
	onBeforeUnmount(() => observer?.disconnect());

	return costing;
}
