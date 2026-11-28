<script setup>
import { computed, ref, watch } from "vue";
import { Button, Dialog, TextInput } from "frappe-ui";
import EmployeeTile from "../EmployeeTile.vue";
import { __, call } from "../../lib/api";
import { session } from "../../lib/session";

const open = defineModel("open");
const props = defineProps({ jobCard: Object, mode: { type: String, default: "start" } });
const emit = defineEmits(["confirm"]);

const picked = ref([]);
const query = ref("");
const employees = ref([]);

const PRESET = {
	start: (row) => (row.assigned.length ? [...row.assigned] : [session.employee.name]),
	change: (row) => [...row.crew],
	assign: (row) => [...row.assigned],
};
const TEXT = {
	start: { title: "Who is working on this job?", hint: "Time is logged for each person you pick." },
	change: { title: "Change the crew", hint: "Time is logged for each person you pick, from now on." },
	assign: {
		title: "Assign job card",
		hint: "Only the people you pick see this job card on the Shop Floor.",
	},
};

async function load() {
	employees.value = await call("get_employees", {
		plant_floor: session.plantFloor,
		search: query.value || null,
	});
}

watch(open, (isOpen) => {
	if (!isOpen) return;
	query.value = "";
	picked.value = PRESET[props.mode](props.jobCard);
	load();
});
watch(query, load);

const candidates = computed(() =>
	[...employees.value].sort(
		(a, b) => props.jobCard.assigned.includes(b.name) - props.jobCard.assigned.includes(a.name)
	)
);

function toggle(row) {
	picked.value = picked.value.includes(row.name)
		? picked.value.filter((name) => name !== row.name)
		: [...picked.value, row.name];
}

function confirm() {
	emit("confirm", picked.value);
	open.value = false;
}

const action = computed(() => {
	if (props.mode === "start") return __("Start with {0} people", [picked.value.length]);
	if (props.mode === "assign") return __("Assign to {0} people", [picked.value.length]);
	return __("Update Crew");
});
</script>

<template>
	<Dialog v-model:open="open" :title="__(TEXT[mode].title)" size="2xl">
		<div class="space-y-4">
			<p class="text-p-sm text-ink-gray-6">
				{{ jobCard?.name }} · {{ jobCard?.operation }}. {{ __(TEXT[mode].hint) }}
			</p>
			<TextInput
				v-model="query"
				size="lg"
				:placeholder="__('Name or badge')"
				:aria-label="__('Find employee')"
			>
				<template #prefix
					><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
				/></template>
			</TextInput>
			<div class="grid max-h-[22rem] gap-2 overflow-y-auto sm:grid-cols-2">
				<EmployeeTile
					v-for="row in candidates"
					:key="row.name"
					:employee="row"
					selectable
					:selected="picked.includes(row.name)"
					:assigned="jobCard?.assigned.includes(row.name)"
					@pick="toggle"
				/>
			</div>
			<div class="flex justify-end gap-2 pt-2">
				<Button size="lg" :label="__('Cancel')" @click="open = false" />
				<Button
					size="lg"
					variant="solid"
					:label="action"
					:disabled="!picked.length"
					@click="confirm"
				/>
			</div>
		</div>
	</Dialog>
</template>
