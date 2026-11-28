<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Button, FormControl, TabButtons } from "frappe-ui";
import JobCardRow from "../components/JobCardRow.vue";
import CrewDialog from "../components/station/CrewDialog.vue";
import { __, call, notify } from "../lib/api";
import { session, setPlantFloor } from "../lib/session";

const show = ref("open");
const operation = ref("");
const jobCards = ref([]);
const picked = ref(null);
const assignOpen = ref(false);

async function load() {
	jobCards.value = await call("get_job_cards", {
		plant_floor: session.plantFloor,
		show: show.value,
		operation: operation.value || null,
	});
}

onMounted(load);
watch([show, operation, () => session.plantFloor], load);

const operations = computed(() => [
	{ label: __("All Operations"), value: "" },
	...[...new Set(jobCards.value.map((row) => row.operation))].map((value) => ({ label: value, value })),
]);

function openAssign(row) {
	picked.value = row;
	assignOpen.value = true;
}

async function assign(employees) {
	await call("assign_job_card", { job_card: picked.value.name, employees });
	notify(__("{0} assigned", [picked.value.name]));
	await load();
}
</script>

<template>
	<div class="mx-auto max-w-[1280px] space-y-6 px-3 pt-6 pb-16 sm:px-5">
		<div>
			<h1 class="text-3xl font-semibold text-ink-gray-9">{{ __("Job Cards") }}</h1>
			<p class="mt-1 text-p-base text-ink-gray-6">
				{{
					__(
						"Assign each job card to the operators who work on it. Operators see only the job cards assigned to them."
					)
				}}
			</p>
		</div>
		<div class="flex flex-wrap items-end gap-3">
			<div v-if="session.context.plant_floors.length > 1" class="w-64 shrink-0">
				<FormControl
					type="select"
					:label="__('Plant Floor')"
					:model-value="session.plantFloor"
					:options="
						session.context.plant_floors.map((row) => ({ label: row.name, value: row.name }))
					"
					@update:model-value="setPlantFloor"
				/>
			</div>
			<div class="w-56 shrink-0">
				<FormControl
					v-model="operation"
					type="select"
					:label="__('Operation')"
					:options="operations"
				/>
			</div>
			<TabButtons
				v-model="show"
				class="ml-auto"
				:options="[
					{ label: __('Open'), value: 'open' },
					{ label: __('Unassigned'), value: 'unassigned' },
					{ label: __('Completed'), value: 'completed' },
				]"
			/>
		</div>
		<div
			v-if="jobCards.length"
			class="divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-2"
		>
			<JobCardRow v-for="row in jobCards" :key="row.name" :job-card="row">
				<Button
					v-if="show !== 'completed'"
					size="lg"
					:variant="row.assigned.length ? 'subtle' : 'solid'"
					icon-left="lucide-user-plus"
					:label="row.assigned.length ? __('Reassign') : __('Assign')"
					@click="openAssign(row)"
				/>
			</JobCardRow>
		</div>
		<div
			v-else
			class="flex flex-col items-center gap-3 rounded-5 border border-outline-gray-2 py-16 text-center"
		>
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span class="lucide-clipboard-check block size-6" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-7">{{ __("No job cards here") }}</p>
		</div>
		<CrewDialog
			v-if="picked"
			v-model:open="assignOpen"
			:job-card="picked"
			mode="assign"
			@confirm="assign"
		/>
	</div>
</template>
