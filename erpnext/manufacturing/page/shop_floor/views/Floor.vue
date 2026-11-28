<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Button, FormControl, TabButtons } from "frappe-ui";
import StationTile from "../components/StationTile.vue";
import JobCardRow from "../components/JobCardRow.vue";
import FloorScene from "../components/FloorScene.vue";
import { __, call, go } from "../lib/api";
import { isManager, session, setPlantFloor, usePolling } from "../lib/session";

const props = defineProps({ query: Object });

const floor = ref(null);
const myJobCards = ref([]);
const view = ref(props.query?.view === "3d" ? "3d" : "board");

async function load() {
	const [floorData, jobCards] = await Promise.all([
		session.plantFloor ? call("get_floor", { plant_floor: session.plantFloor }) : null,
		isManager.value ? [] : call("get_my_job_cards", { employee: session.employee.name }),
	]);
	floor.value = floorData;
	myJobCards.value = jobCards;
	const myFloor = jobCards.find((row) => row.plant_floor)?.plant_floor;
	if (myFloor && !jobCards.some((row) => row.plant_floor === session.plantFloor)) setPlantFloor(myFloor);
}

const polling = usePolling(load);
onMounted(() => {
	load();
	polling.start();
});
onBeforeUnmount(polling.stop);
watch(() => session.plantFloor, load);

const workstations = computed(() => floor.value?.lines.flatMap((line) => line.workstations) || []);
const myStations = computed(() => [...new Set(myJobCards.value.map((row) => row.workstation))]);
const down = computed(() => workstations.value.filter((row) => row.status === "Problem"));
const stats = computed(() => floor.value?.stats || {});
const kpis = computed(() => [
	{ label: __("Running"), value: stats.value.running, dot: "bg-surface-green-7" },
	{ label: __("Idle"), value: stats.value.idle, dot: "bg-surface-gray-5" },
	{ label: __("Down"), value: stats.value.down, dot: "bg-surface-red-7" },
	{ label: __("Maintenance"), value: stats.value.maintenance, dot: "bg-surface-amber-7" },
	{ label: __("Downtime Today"), value: __("{0} min", [stats.value.downtime_minutes || 0]) },
	{ label: __("Job Cards Done Today"), value: stats.value.completed },
]);
const views = computed(() => [
	{ label: isManager.value ? __("Board") : __("My Job Cards"), value: "board" },
	{ label: __("3D Layout"), value: "3d" },
]);
const subtitle = computed(() => {
	if (isManager.value) return __("Every workstation on {0}.", [session.plantFloor]);
	const count = myJobCards.value.length;
	if (!count) return __("No job cards are assigned to you yet.");
	return count === 1
		? __("You have 1 job card assigned.")
		: __("You have {0} job cards assigned.", [count]);
});
</script>

<template>
	<div class="mx-auto max-w-[1280px] space-y-8 px-3 pt-6 pb-16 sm:px-5">
		<div class="flex flex-wrap items-end gap-3">
			<div class="min-w-0 flex-1">
				<h1 class="text-3xl font-semibold text-ink-gray-9">
					{{ __("Hello, {0}", [session.employee.employee_name]) }}
				</h1>
				<p class="mt-1 text-p-base text-ink-gray-6">{{ subtitle }}</p>
			</div>
			<div v-if="session.context.plant_floors.length > 1" class="w-64 shrink-0">
				<FormControl
					type="select"
					:aria-label="__('Plant Floor')"
					:model-value="session.plantFloor"
					:options="
						session.context.plant_floors.map((row) => ({ label: row.name, value: row.name }))
					"
					@update:model-value="setPlantFloor"
				/>
			</div>
			<TabButtons v-model="view" :options="views" />
		</div>

		<div
			v-if="!session.plantFloor"
			class="rounded-5 border border-outline-gray-2 px-4 py-10 text-center text-base text-ink-gray-6"
		>
			{{ __("Create a Plant Floor and set it on your Workstations to see them here.") }}
		</div>

		<template v-else-if="floor">
			<div
				class="grid grid-cols-2 divide-outline-gray-2 rounded-5 border border-outline-gray-2 sm:grid-cols-3 lg:grid-cols-6 lg:divide-x"
			>
				<div v-for="kpi in kpis" :key="kpi.label" class="px-4 py-3">
					<p class="flex items-center gap-1.5 text-sm text-ink-gray-5">
						<span
							v-if="kpi.dot"
							class="size-2 rounded-full"
							:class="kpi.dot"
							aria-hidden="true"
						/>{{ kpi.label }}
					</p>
					<p class="mt-1 text-2xl font-semibold tabular-nums text-ink-gray-9">
						{{ kpi.value ?? 0 }}
					</p>
				</div>
			</div>

			<div v-if="isManager && down.length" class="space-y-2">
				<div
					v-for="row in down"
					:key="row.name"
					class="flex items-center gap-3 rounded-5 bg-surface-red-2 px-4 py-3"
				>
					<span class="lucide-triangle-alert size-5 shrink-0 text-ink-red-5" aria-hidden="true" />
					<p class="min-w-0 flex-1 truncate text-base font-medium text-ink-gray-9">
						{{ __("{0} is stopped for a breakdown", [row.name]) }}
					</p>
					<Button :label="__('Open')" @click="go('station', row.name)" />
				</div>
			</div>

			<FloorScene
				v-if="view === '3d'"
				:key="session.plantFloor"
				class="h-[calc(100vh-20rem)] min-h-[32rem]"
				:lines="floor.lines"
				:highlight="isManager ? [] : myStations"
				:allowed="isManager ? null : myStations"
			/>

			<template v-else-if="isManager">
				<section v-for="line in floor.lines" :key="line.name" class="space-y-3">
					<h2 class="text-lg font-semibold text-ink-gray-8">
						{{ line.name || __("Other Workstations") }}
					</h2>
					<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
						<StationTile v-for="row in line.workstations" :key="row.name" :workstation="row" />
					</div>
				</section>
			</template>

			<section v-else class="space-y-3">
				<h2 class="text-lg font-semibold text-ink-gray-8">{{ __("My Job Cards") }}</h2>
				<div
					v-if="myJobCards.length"
					class="divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-2"
				>
					<JobCardRow v-for="row in myJobCards" :key="row.name" :job-card="row">
						<Button
							size="lg"
							variant="solid"
							icon-right="lucide-arrow-right"
							:label="__('Open')"
							@click="go('station', row.workstation)"
						/>
					</JobCardRow>
				</div>
				<div
					v-else
					class="flex flex-col items-center gap-3 rounded-5 border border-outline-gray-2 py-16 text-center"
				>
					<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
						<span class="lucide-clipboard-list block size-6" aria-hidden="true" />
					</div>
					<p class="text-base text-ink-gray-7">{{ __("No job cards assigned to you") }}</p>
					<p class="text-sm text-ink-gray-5">
						{{ __("Your supervisor assigns job cards in the Employee field of the Job Card.") }}
					</p>
				</div>
			</section>
		</template>
	</div>
</template>
