<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Avatar, Button, Dropdown } from "frappe-ui";
import SignIn from "./views/SignIn.vue";
import Floor from "./views/Floor.vue";
import Station from "./views/Station.vue";
import JobCards from "./views/JobCards.vue";
import LoadFailed from "../plant_builder/components/LoadFailed.vue";
import { __, go } from "./lib/api";
import { canSwitchOperator, isManager, loadContext, session, signOut } from "./lib/session";

const props = defineProps({
	route: { type: Array, default: () => [] },
	query: { type: Object, default: () => ({}) },
});
const emit = defineEmits(["title", "actions"]);

const ready = ref(false);
const failed = ref(false);
const view = computed(() => props.route[0] || "floor");
const workstation = computed(() => (props.route[1] ? decodeURIComponent(props.route[1]) : null));

async function load() {
	failed.value = false;
	try {
		await loadContext();
		ready.value = true;
	} catch {
		failed.value = true;
	}
}

onMounted(load);
watch(
	() => [view.value, workstation.value],
	() => emit("title", workstation.value || __("Shop Floor")),
	{ immediate: true }
);

const menu = computed(() => [
	...(canSwitchOperator.value
		? [{ label: __("Switch Operator"), icon: "lucide-users", onClick: switchOperator }]
		: []),
	...(isManager.value
		? [{ label: __("Job Cards"), icon: "lucide-clipboard-list", onClick: () => go("job-cards") }]
		: []),
]);

function switchOperator() {
	signOut();
	go();
}
</script>

<template>
	<div
		class="flex h-full flex-col bg-surface-base text-ink-gray-9 [&_input[type=number]::-webkit-inner-spin-button]:appearance-none [&_input[type=number]::-webkit-outer-spin-button]:appearance-none [&_input[type=number]]:[appearance:textfield]"
	>
		<LoadFailed v-if="failed" @retry="load" />
		<template v-else-if="ready">
			<div
				v-if="session.employee"
				class="flex items-center justify-end gap-2 border-b border-outline-gray-1 px-3 py-2 sm:px-5"
			>
				<Button
					v-if="view !== 'floor'"
					variant="ghost"
					icon-left="lucide-layout-grid"
					:label="__('Plant Floor')"
					@click="go()"
				/>
				<Dropdown v-if="menu.length" :options="menu">
					<Button variant="ghost" size="lg" :label="session.employee.employee_name">
						<template #prefix
							><Avatar
								:label="session.employee.employee_name"
								:image="session.employee.image"
								size="md"
						/></template>
					</Button>
				</Dropdown>
				<div v-else class="flex items-center gap-2 px-2 text-base text-ink-gray-8">
					<Avatar
						:label="session.employee.employee_name"
						:image="session.employee.image"
						size="md"
					/>{{ session.employee.employee_name }}
				</div>
			</div>
			<div class="min-h-0 flex-1 overflow-y-auto">
				<SignIn v-if="!session.employee" />
				<Station
					v-else-if="view === 'station' && workstation"
					:key="workstation"
					:workstation="workstation"
				/>
				<JobCards v-else-if="view === 'job-cards' && isManager" />
				<Floor v-else :query="query" />
			</div>
		</template>
	</div>
</template>
