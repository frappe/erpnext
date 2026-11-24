// The Project form owns the Tasks tab: it loads the tasks, holds the toolbar and opens desk's task
// dialogs. The island asks it for things with DOM events, which leave the shadow root.
export function create_host_events(element) {
	return (name, detail) =>
		element.value?.dispatchEvent(new CustomEvent(name, { bubbles: true, composed: true, detail }));
}
