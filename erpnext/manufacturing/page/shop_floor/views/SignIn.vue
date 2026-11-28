<script setup>
import { onMounted, ref, watch } from "vue";
import { FormControl, TextInput } from "frappe-ui";
import EmployeeTile from "../components/EmployeeTile.vue";
import { __, call, notify } from "../lib/api";
import { session, setPlantFloor, signIn } from "../lib/session";

const query = ref("");
const employees = ref([]);
let timer = null;

async function load() {
	employees.value = await call("get_employees", {
		plant_floor: session.plantFloor,
		search: query.value || null,
	});
}

watch(query, () => {
	clearTimeout(timer);
	timer = setTimeout(load, 250);
});
watch(() => session.plantFloor, load);
onMounted(load);

function pick(employee) {
	signIn(employee);
	notify(__("Signed in as {0}", [employee.employee_name]));
}

function scan() {
	const exact = employees.value.find((row) => row.name.toLowerCase() === query.value.trim().toLowerCase());
	const only = employees.value.length === 1 ? employees.value[0] : null;
	if (exact || only) pick(exact || only);
}
</script>

<template>
	<div class="mx-auto max-w-4xl px-3 pt-10 pb-16 sm:px-5">
		<h1 class="text-3xl font-semibold text-ink-gray-9">{{ __("Who is on shift?") }}</h1>
		<p class="mt-1.5 text-p-base text-ink-gray-6">
			{{
				__(
					"Tap your name or scan your badge. You see the job cards assigned to you, and the time and quantities you log are recorded against you."
				)
			}}
		</p>
		<div class="mt-6 flex flex-wrap items-end gap-3">
			<TextInput
				v-model="query"
				size="lg"
				class="w-full max-w-md"
				:placeholder="__('Badge or name')"
				:aria-label="__('Badge or name')"
				@keydown.enter="scan"
			>
				<template #prefix
					><span class="lucide-scan-barcode size-4 text-ink-gray-5" aria-hidden="true"
				/></template>
			</TextInput>
			<div v-if="session.context.plant_floors.length > 1" class="w-64 shrink-0">
				<FormControl
					type="select"
					size="lg"
					:label="__('Plant Floor')"
					:model-value="session.plantFloor"
					:options="
						session.context.plant_floors.map((row) => ({ label: row.name, value: row.name }))
					"
					@update:model-value="setPlantFloor"
				/>
			</div>
		</div>
		<div v-if="employees.length" class="mt-6 grid gap-3 sm:grid-cols-2">
			<EmployeeTile v-for="row in employees" :key="row.name" :employee="row" @pick="pick" />
		</div>
		<div v-else class="flex flex-col items-center gap-3 py-16 text-center">
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span class="lucide-user-x block size-6" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-7">{{ __("No employee found") }}</p>
			<p class="text-sm text-ink-gray-5">
				{{ __("Check the badge number, or ask your supervisor to add you as an active Employee.") }}
			</p>
		</div>
	</div>
</template>
