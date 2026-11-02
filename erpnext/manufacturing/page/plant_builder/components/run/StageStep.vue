<script setup>
import { computed, inject, ref } from "vue";
import { Button, Progress } from "frappe-ui";
import StepHeader from "./StepHeader.vue";
import StageInputs from "./StageInputs.vue";
import StageOutput from "./StageOutput.vue";
import BreakdownPanel from "./BreakdownPanel.vue";
import { __ } from "../../lib/api";
import { MACHINES } from "../../lib/machines";
import { fmt, fmtTimer, num, round } from "../../lib/format";

const props = defineProps({ stage: Object, index: Number });
const run = inject("run");

const machine = computed(() => MACHINES[run.plant.value.stages[props.index]?.machine] || MACHINES.generic);
const plantStage = computed(() => run.state.value.plant.doc.stages[props.index] || {});
const plan = computed(() => run.state.value.plan);
const meta = computed(() => {
	const pack = props.stage.is_packing;
	const loss = round(100 - num(plantStage.value.yield_percentage || 100), 2);
	const unit = (props.stage.output.uom || "").toLowerCase();
	const instruction = pack
		? __("{0} {1} {2} into each {3}, then seal and label it.", [
				machine.value.verb,
				fmt(plan.value.weight_per_unit),
				plan.value.weight_uom,
				unit,
		  ])
		: __("{0} for {1} minutes.", [machine.value.verb, fmt(props.stage.planned_minutes)]) +
		  (loss > 0 ? " " + __("About {0}% of the weight is lost here.", [fmt(loss)]) : "");
	return {
		pack,
		instruction,
		action: pack ? __("Produce Finished Goods") : __("Produce {0}", [props.stage.output.item_name]),
	};
});

const canStart = computed(() => props.stage.can_start && run.state.value.work_order.docstatus === 1);
const hasInputs = computed(() => props.stage.items.some((row) => row.is_input));
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
		processing: { label: machine.value.verb, theme: "amber" },
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
const lotOutput = computed(() => {
	const output = props.stage.output;
	return __("This lot makes about {0} {1} {2}", [
		fmt(run.plannedOutput(props.stage)),
		output.uom,
		output.item_name,
	]);
});

const inputErrors = computed(() => {
	if (props.stage.phase !== "ready") return [];
	const errors = props.stage.items.flatMap((row) => rowErrors(row, run.actualOf(props.stage, row)));
	if (hasInputs.value && run.plannedOutput(props.stage) <= 0) {
		errors.push(__("Pass some of the semi-finished goods to this stage"));
	}
	return errors;
});

function rowErrors(row, actual) {
	if (row.is_input) {
		if (actual >= 0 && actual <= row.waiting_qty + 0.0001) return [];
		const values = [fmt(row.waiting_qty), row.uom, row.item_name, row.source_stage];
		return [__("Only {0} {1} of {2} is waiting from {3}", values)];
	}
	if (actual <= 0) return [__("{0} needs a quantity above zero", [row.item_name])];
	if (actual > row.available_qty + 0.0001) {
		return [__("Only {0} {1} of {2} is in stock", [fmt(row.available_qty), row.uom, row.item_name])];
	}
	const planned = run.plannedOf(props.stage, row);
	if (row.is_balance_item || !planned) return [];
	const tolerance = num(run.state.value.plant.doc.formula_tolerance);
	const variance = ((actual - planned) / planned) * 100;
	if (Math.abs(variance) <= tolerance + 0.0001) return [];
	return [
		__("{0} is {1}% {2} the formula. The allowed range is ±{3}%.", [
			row.item_name,
			fmt(round(Math.abs(variance), 1)),
			variance > 0 ? __("over") : __("under"),
			fmt(tolerance),
		]),
	];
}
</script>

<template>
	<div>
		<StepHeader
			:no="stage.idx"
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
			<template v-if="stage.phase === 'ready'">
				<p v-if="hasInputs" class="text-p-sm text-ink-gray-6">{{ lotOutput }}</p>
				<p v-for="error in inputErrors" :key="error" class="text-p-sm text-ink-red-5">{{ error }}</p>
				<Button
					variant="solid"
					icon-left="lucide-arrow-down-to-line"
					:label="__('Consume Materials')"
					class="w-full"
					:loading="run.busy.value"
					:disabled="inputErrors.length > 0 || run.paused.value"
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
