<script setup>
import { computed, inject, ref } from "vue";
import { Button, Progress } from "frappe-ui";
import StepHeader from "./StepHeader.vue";
import StageInputs from "./StageInputs.vue";
import StageOutput from "./StageOutput.vue";
import BreakdownPanel from "./BreakdownPanel.vue";
import { __ } from "../../lib/api";
import { machineOf } from "../../lib/machines";
import { fmt, fmtTimer, num, round } from "../../lib/format";

const props = defineProps({ stage: Object, index: Number });
const run = inject("run");

const machine = computed(() => machineOf(props.stage.machine_model));
const plantStage = computed(() => run.state.value.plant.doc.stages[props.index] || {});
const plan = computed(() => run.state.value.plan);
const meta = computed(() => {
	const pack = props.stage.is_packing;
	const loss = round(100 - num(plantStage.value.yield_percentage || 100), 2);
	const unit = (props.stage.output.uom || "").toLowerCase();
	const instruction = pack
		? __("{0} {1} {2} into each {3}, then seal and label it.", [
				__(machine.value.verb),
				fmt(plan.value.weight_per_unit),
				plan.value.weight_uom,
				unit,
		  ])
		: __("{0} for {1} minutes.", [__(machine.value.verb), fmt(props.stage.planned_minutes)]) +
		  (loss > 0 ? " " + __("About {0}% of the weight is lost here.", [fmt(loss)]) : "");
	return {
		pack,
		instruction,
		action: pack ? __("Produce Finished Goods") : __("Produce {0}", [props.stage.output.item_name]),
	};
});

const canStart = computed(() => props.stage.can_start && run.state.value.work_order.docstatus === 1);
const status = computed(() => {
	if (canStart.value) return "active";
	return { waiting: "waiting", done: "done" }[props.stage.phase] ?? "active";
});
const busy = computed(() => ["charging", "processing"].includes(props.stage.phase));
const confirmingBreakdown = ref(false);
const canReportBreakdown = computed(
	() => ["ready", "processing", "review"].includes(props.stage.phase) && !run.paused.value
);
async function reportBreakdown() {
	await run.reportBreakdown(props.stage);
	confirmingBreakdown.value = false;
}

const badge = computed(() => {
	const phase = props.stage.phase;
	if (props.stage.breakdown) return { label: __("Breakdown"), theme: "red" };
	if (run.paused.value && !["waiting", "done"].includes(phase))
		return { label: __("On Hold"), theme: "amber" };
	return {
		waiting: { label: __("Waiting"), theme: "gray" },
		ready: { label: __("Ready"), theme: "blue" },
		charging: { label: __("Charging"), theme: "amber" },
		processing: { label: __(machine.value.verb), theme: "amber" },
		review: { label: __("Record Output"), theme: "blue" },
		done: { label: __("Done"), theme: "green" },
	}[phase];
});
const waitingFor = computed(() => {
	const stages = props.stage.inputs.filter((row) => row.waiting_qty <= 0).map((row) => row.stage_name);
	return [...new Set(stages)];
});
const subtitle = computed(() => {
	const { output, lot, phase, workstation } = props.stage;
	if (phase === "done") {
		const made = __("Made {0} {1} {2}", [fmt(output.completed_qty), output.uom, output.item_name]);
		return lot > 1 ? `${made} · ${__("{0} lots", [lot])}` : made;
	}
	if (
		phase === "waiting" &&
		!canStart.value &&
		waitingFor.value.length &&
		run.state.value.work_order.docstatus
	) {
		return __("Waits for {0}", [waitingFor.value.join(", ")]);
	}
	return lot > 1 ? `${__("Lot {0}", [lot])} · ${workstation}` : workstation;
});
const preview = computed(() => run.previewOf(props.stage));
const makes = computed(() => {
	const output = props.stage.output;
	const qty = preview.value?.output_qty ?? (output.expected_qty || output.planned_qty);
	return { name: output.item_name || output.item_code, qty: `${fmt(round(qty, 3))} ${output.uom || ""}` };
});
const inputErrors = computed(() =>
	props.stage.phase === "ready" ? [...(preview.value?.errors || []), ...run.pickErrors(props.stage)] : []
);
const canConsume = computed(
	() => preview.value && !run.isPreviewing(props.stage) && !inputErrors.value.length && !run.paused.value
);
</script>

<template>
	<div>
		<StepHeader
			:icon="machine.icon"
			:title="stage.stage_name"
			:subtitle="subtitle"
			:status="status"
			:badge="badge"
		/>
		<div v-if="status === 'active' && stage.breakdown" class="px-3 pb-4">
			<BreakdownPanel :stage="stage" />
		</div>
		<div v-else-if="status === 'active'" class="space-y-4 px-3 pb-4">
			<p class="text-p-sm text-ink-gray-6">{{ meta.instruction }}</p>
			<template v-if="canStart">
				<p class="text-p-sm text-ink-amber-5">
					{{
						__("{0} is busy with another batch. Start this stage when it is free.", [
							stage.workstation,
						])
					}}
				</p>
				<Button
					variant="solid"
					icon-left="lucide-play"
					:label="__('Start Stage')"
					class="w-full"
					:loading="run.busy.value"
					@click="run.start(stage)"
				/>
			</template>
			<StageInputs
				v-if="!canStart && stage.phase !== 'review'"
				:stage="stage"
				:editable="stage.phase === 'ready' && !run.paused.value"
			/>
			<div
				v-if="stage.phase !== 'review' && stage.output.item_code"
				class="flex items-center gap-2 rounded-4 bg-surface-gray-1 px-3 py-2"
			>
				<span class="lucide-package-check size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
				<div class="min-w-0 flex-1">
					<p class="text-xs text-ink-gray-5">{{ __("Makes") }}</p>
					<p class="truncate text-sm font-medium text-ink-gray-8" :title="makes.name">
						{{ makes.name }}
					</p>
				</div>
				<p class="shrink-0 text-sm font-medium tabular-nums text-ink-gray-8">{{ makes.qty }}</p>
			</div>
			<template v-if="stage.phase === 'ready'">
				<p v-for="error in inputErrors" :key="error" class="text-p-sm text-ink-red-5">{{ error }}</p>
				<Button
					variant="solid"
					icon-left="lucide-arrow-down-to-line"
					:label="__('Consume Materials')"
					class="w-full"
					:loading="run.busy.value"
					:disabled="!canConsume"
					@click="run.consume(stage)"
				/>
			</template>
			<div v-else-if="busy" class="space-y-2">
				<div class="flex items-center justify-between gap-3 text-sm">
					<span class="truncate text-ink-gray-7">{{ run.activityOf(stage) }}</span>
					<span class="w-10 shrink-0 text-right tabular-nums text-ink-gray-5"
						>{{ Math.round(run.progressOf(stage)) }}%</span
					>
				</div>
				<Progress :value="run.progressOf(stage)" size="sm" />
				<div class="flex items-center gap-1.5 pt-1 text-xs text-ink-gray-5">
					<span class="lucide-timer size-3.5" aria-hidden="true" />
					<span>{{ __("Stage timer") }}</span>
					<span class="tabular-nums text-ink-gray-7">{{ fmtTimer(run.stageSeconds(stage)) }}</span>
				</div>
				<Button
					v-if="stage.phase === 'processing'"
					icon-left="lucide-clipboard-check"
					:label="__('Record Output')"
					class="w-full"
					:disabled="run.paused.value"
					@click="run.openReview(stage)"
				/>
			</div>
			<StageOutput v-else-if="stage.phase === 'review'" :stage="stage" :meta="meta" />
			<div
				v-if="canReportBreakdown && confirmingBreakdown"
				class="space-y-3 rounded-4 border border-outline-red-2 bg-surface-red-1 p-3"
			>
				<p class="text-p-sm text-ink-gray-8">
					{{
						__("Stop {0} for a breakdown? Its timer stops until you restart it.", [
							stage.workstation,
						])
					}}
				</p>
				<div class="flex gap-2">
					<Button
						variant="solid"
						theme="red"
						icon-left="lucide-octagon-x"
						:label="__('Stop Machine')"
						:loading="run.busy.value"
						@click="reportBreakdown"
					/>
					<Button :label="__('Cancel')" @click="confirmingBreakdown = false" />
				</div>
			</div>
			<Button
				v-else-if="canReportBreakdown"
				variant="ghost"
				theme="red"
				icon-left="lucide-triangle-alert"
				:label="__('Report Machine Breakdown')"
				class="w-full"
				@click="confirmingBreakdown = true"
			/>
		</div>
	</div>
</template>
