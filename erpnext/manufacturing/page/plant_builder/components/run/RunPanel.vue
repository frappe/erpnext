<script setup>
import { computed, inject, ref, watch } from "vue";
import { Alert, ScrollArea } from "frappe-ui";
import PlanStep from "./PlanStep.vue";
import StageStep from "./StageStep.vue";
import DoneSummary from "./DoneSummary.vue";
import EntryLog from "./EntryLog.vue";
import { __ } from "../../lib/api";

const run = inject("run");
const steps = ref([]);
const running = computed(() =>
	run.stages.value
		.filter(run.isActive)
		.map((stage) => stage.idx)
		.join()
);

watch(
	running,
	(value) => {
		const index = run.stages.value.findIndex(run.isActive);
		const step = value && steps.value[index]?.$el;
		const viewport = step?.closest("[data-reka-scroll-area-viewport]");
		if (!viewport) return;
		const top = step.getBoundingClientRect().top - viewport.getBoundingClientRect().top;
		viewport.scrollTo({ top: viewport.scrollTop + top - 16, behavior: "smooth" });
	},
	{ flush: "post", immediate: true }
);
</script>

<template>
	<aside class="flex min-h-0 flex-col bg-surface-base">
		<ScrollArea class="min-h-0 flex-1" viewport-class="px-4 pt-4 pb-10">
			<Alert
				v-if="run.paused.value"
				class="mb-4"
				theme="amber"
				:title="__('Work Order is on hold')"
				:description="
					__('The timer and the machines are stopped. Resume to carry on from where you left off.')
				"
			/>
			<DoneSummary v-if="run.status.value === 'Completed'" class="mb-4" />
			<div class="divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-2">
				<PlanStep />
				<StageStep
					v-for="(stage, i) in run.stages.value"
					:key="stage.idx"
					:stage="stage"
					:ref="(step) => (steps[i] = step)"
					:index="i"
				/>
			</div>
			<EntryLog class="mt-6" />
		</ScrollArea>
	</aside>
</template>
