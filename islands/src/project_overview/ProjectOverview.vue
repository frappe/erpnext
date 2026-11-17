<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Button } from "frappe-ui";
import { ChartCard, ChartContainer } from "frappe-ui/charts";
import { useHost } from "@framework/ui/island";

import { useOnScreenCall } from "../project_costing/useProjectCosting.js";
import AttentionList from "./components/AttentionList.vue";
import EmptyState from "./components/EmptyState.vue";
import OverviewHeader from "./components/OverviewHeader.vue";
import PeopleCard from "./components/PeopleCard.vue";
import ProfitabilityCard from "./components/ProfitabilityCard.vue";
import ProgressChart from "./components/ProgressChart.vue";
import StatCards from "./components/StatCards.vue";
import TaskDonut from "./components/TaskDonut.vue";
import { createFormat, provideFormat } from "./format.js";
import { createActions, provideActions } from "./host.js";

const OVERVIEW = "/api/v2/method/erpnext.projects.doctype.project.project_overview.get_project_overview";

const props = defineProps({
	doctype: { type: String, default: "Project" },
	name: { type: String, default: null },
	doc: { type: Object, default: () => ({}) },
	is_new: { type: Boolean, default: false },
	read_only: { type: Boolean, default: false },
});

const __ = window.__;
const host = useHost();
const element = ref(null);
provideFormat(createFormat(host));
const actions = createActions(element, host, () => props.name);
provideActions(actions);

const refreshes = ref(0);
const on_form_refresh = (event) => event.detail?.project === props.name && refreshes.value++;
onMounted(() => document.addEventListener("project-overview-refresh", on_form_refresh));
onBeforeUnmount(() => document.removeEventListener("project-overview-refresh", on_form_refresh));
const call = useOnScreenCall(
	element,
	OVERVIEW,
	() => props.name,
	() => refreshes.value
);
// the island stays mounted when another Project opens
const data = computed(() => (call.data?.project === props.name ? call.data : null));
const failed = computed(() => Boolean(call.error || data.value?.errors.summary));
const loading = computed(() => !failed.value && !data.value);

const has_chart = computed(() => {
	const chart = data.value.planned_vs_completed;
	return !chart || chart.points.length > 0;
});
const show_profitability = computed(() =>
	Boolean(data.value.profitability || data.value.errors.profitability)
);
const can_add_task = computed(() => Boolean(window.frappe?.model?.can_create?.("Task")));

const PLACEHOLDERS = [
	__("Planned vs Completed"),
	__("Needs Attention"),
	__("Tasks by Status"),
	__("Open Tasks by Assignee"),
];
</script>

<template>
	<div ref="element" class="flex flex-col gap-5 pb-8 pt-2" :aria-busy="loading">
		<template v-if="!is_new">
			<OverviewHeader :data="data" :doc="doc" />

			<template v-if="loading || failed">
				<StatCards :data="null" :loading="loading" :project="name" />
				<div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))] gap-4">
					<ChartCard v-for="title in PLACEHOLDERS" :key="title" class="h-[220px]">
						<ChartContainer
							:title="title"
							:loading="loading"
							:error="loading ? null : __('Could not load tasks')"
						>
							<template #error>
								<span class="text-sm-medium text-ink-red-7">{{
									__("Could not load tasks")
								}}</span>
							</template>
						</ChartContainer>
					</ChartCard>
				</div>
				<div v-if="failed" class="flex items-center gap-3 text-sm text-ink-gray-6">
					<span>{{
						__("Could not load the overview. Project details are still on the other tabs.")
					}}</span>
					<Button size="sm" :label="__('Retry')" @click="call.reload()" />
				</div>
			</template>

			<EmptyState
				v-else-if="!data.summary.has_tasks"
				icon="lucide-square-check"
				:title="__('No tasks yet')"
				:description="
					__(
						'Progress, deadlines, workload and costs for this project will show up here once tasks are added.'
					)
				"
				:actions="
					can_add_task
						? [{ label: __('New Task'), icon: 'lucide-plus', onClick: actions.new_task }]
						: []
				"
			/>

			<EmptyState
				v-else-if="data.summary.all_cancelled"
				icon="lucide-circle-x"
				:title="__('All tasks were cancelled')"
				:description="
					__(
						'None of this project\'s {0} tasks went ahead, so there is no progress or workload to show.',
						[data.summary.task_count]
					)
				"
				:actions="[
					{ label: __('View Tasks'), onClick: () => actions.open_list('Task', { project: name }) },
				]"
			/>

			<template v-else>
				<StatCards :data="data" :project="name" />

				<template v-if="has_chart">
					<div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))] gap-4">
						<ProgressChart :chart="data.planned_vs_completed" :delivery="data.delivery" />
						<TaskDonut
							:breakdown="data.delivery ? data.tasks_by_delivery : data.tasks_by_status"
							:delivery="Boolean(data.delivery)"
						/>
					</div>
					<AttentionList :data="data" />
					<div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))] gap-4">
						<PeopleCard :data="data" />
						<ProfitabilityCard v-if="show_profitability" :profitability="data.profitability" />
					</div>
				</template>

				<template v-else>
					<AttentionList :data="data" />
					<div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))] gap-4">
						<TaskDonut
							:breakdown="data.delivery ? data.tasks_by_delivery : data.tasks_by_status"
							:delivery="Boolean(data.delivery)"
						/>
						<ProfitabilityCard v-if="show_profitability" :profitability="data.profitability" />
					</div>
					<PeopleCard :data="data" />
				</template>
			</template>
		</template>
	</div>
</template>
