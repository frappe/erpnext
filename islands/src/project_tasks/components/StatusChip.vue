<script setup>
import { computed, ref } from "vue";
import { Badge, Dropdown } from "frappe-ui";

import { confirm, set_task_value } from "../lib/api.js";
import { useTasks } from "../lib/context.js";
import { status_theme } from "../lib/tasks.js";

const props = defineProps({
	task: { type: Object, required: true },
});

const __ = window.__;
const tasks = useTasks();
const editable = computed(() => props.task.can_write && tasks.editable.value.includes("status"));

// A long list has a menu per row; each is built the first time its row's chip is clicked, and
// opens straight away.
const active = ref(false);
const open = ref(false);
function activate() {
	active.value = true;
	open.value = true;
}

// Overdue and Template are set by the system, so only the task's own one of them is offered
const options = computed(() =>
	(tasks.options.value.status || [])
		.filter((value) => !["Overdue", "Template"].includes(value) || value === props.task.status)
		.map((value) => ({
			label: __(value),
			selected: value === props.task.status,
			onClick: () => pick(value),
		}))
);

async function pick(value) {
	const { task } = props;
	if (value === task.status) return;
	if (value === "Cancelled") {
		const subject = window.frappe.utils.escape_html(task.subject || task.name);
		if (!(await confirm(__("Cancel task {0}?", [subject])))) return;
	}
	tasks.edit(task, { status: value }, () => set_task_value(task.name, "status", value));
}
</script>

<template>
	<template v-if="task.status">
		<Dropdown v-if="editable && active" v-model:open="open" :options="options">
			<button
				type="button"
				class="relative rounded-full"
				:aria-label="__('Status: {0}', [__(task.status)])"
			>
				<Badge :label="__(task.status)" :theme="status_theme(task.status)" />
			</button>
		</Dropdown>
		<button
			v-else-if="editable"
			type="button"
			class="relative rounded-full"
			:aria-label="__('Status: {0}', [__(task.status)])"
			aria-haspopup="menu"
			@click="activate"
		>
			<Badge :label="__(task.status)" :theme="status_theme(task.status)" />
		</button>
		<Badge v-else :label="__(task.status)" :theme="status_theme(task.status)" />
	</template>
</template>
