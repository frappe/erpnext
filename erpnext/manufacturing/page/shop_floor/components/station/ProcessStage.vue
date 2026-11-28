<script setup>
import { computed, onMounted, provide } from "vue";
import { Button } from "frappe-ui";
import StageStep from "../../../plant_builder/components/run/StageStep.vue";
import LoadFailed from "../../../plant_builder/components/LoadFailed.vue";
import { useRun } from "../../../plant_builder/lib/run";
import { useLoad } from "../../../plant_builder/lib/load";
import { __ } from "../../lib/api";

const props = defineProps({ jobCard: Object });

const run = useRun(props.jobCard.work_order);
provide("run", run);
const { failed, load } = useLoad(run.refresh);
onMounted(load);

const index = computed(() =>
	run.stages.value.findIndex((stage) => (stage.job_cards || []).includes(props.jobCard.name))
);
const openRun = () => window.frappe.set_route("plant-builder", "run", props.jobCard.work_order);
</script>

<template>
	<LoadFailed v-if="failed" @retry="load" />
	<div v-else-if="run.state.value" class="space-y-3">
		<StageStep v-if="index >= 0" :stage="run.stages.value[index]" :index="index" />
		<p v-else class="text-p-sm text-ink-gray-6">
			{{ __("This stage is not part of the current run of the Work Order.") }}
		</p>
		<Button
			variant="ghost"
			icon-left="lucide-factory"
			:label="__('Open the whole run in Plant Builder')"
			@click="openRun"
		/>
	</div>
</template>
