<script setup>
import { computed, ref } from "vue";
import { Dropdown } from "frappe-ui";

import { set_task_value } from "../lib/api.js";
import { useTasks } from "../lib/context.js";
import { PRIORITY_ICONS } from "../lib/tasks.js";

const props = defineProps({
	task: { type: Object, required: true },
});

const __ = window.__;
const tasks = useTasks();
const editable = computed(() => props.task.can_write && tasks.editable.value.includes("priority"));

// A long list has a menu per row; each is built the first time its row's chip is clicked, and
// opens straight away.
const active = ref(false);
const open = ref(false);
function activate() {
	active.value = true;
	open.value = true;
}

const icon = (priority) => PRIORITY_ICONS[priority] || "lucide-signal";

// most urgent first, as the old Tasks tab offered them
const options = computed(() =>
	(tasks.options.value.priority || [])
		.slice()
		.reverse()
		.map((value) => ({
			label: __(value),
			icon: icon(value),
			selected: value === props.task.priority,
			onClick: () => pick(value),
		}))
);

function pick(value) {
	const { task } = props;
	if (value === task.priority) return;
	tasks.edit(task, { priority: value }, () => set_task_value(task.name, "priority", value));
}
</script>

<template>
	<component
		:is="active ? Dropdown : 'span'"
		v-if="task.priority || editable"
		v-bind="active ? { options, open } : {}"
		v-on="active ? { 'update:open': (value) => (open = value) } : {}"
	>
		<component
			:is="editable ? 'button' : 'span'"
			:type="editable ? 'button' : undefined"
			class="relative flex items-center gap-1.5 rounded-4 text-base text-ink-gray-7"
			:aria-label="__('Priority: {0}', [__(task.priority || '')])"
			:aria-haspopup="editable ? 'menu' : undefined"
			@click="editable && !active && activate()"
		>
			<template v-if="task.priority">
				<span
					:class="[
						icon(task.priority),
						task.priority === 'Urgent' ? 'text-ink-red-5' : 'text-ink-gray-6',
					]"
					class="size-4 shrink-0"
					aria-hidden="true"
				/>
				{{ __(task.priority) }}
			</template>
			<span v-else class="lucide-signal size-4 text-ink-gray-4" aria-hidden="true" />
		</component>
	</component>
</template>
