<script setup>
import { computed, onBeforeUnmount, onMounted, provide } from "vue";
import { Badge, Button, Tooltip } from "frappe-ui";
import PlantScene from "../components/three/PlantScene.vue";
import RunPanel from "../components/run/RunPanel.vue";
import { __, openForm } from "../lib/api";
import { levels } from "../lib/clock";
import { machineOf } from "../lib/machines";
import { useRun } from "../lib/run";
import { fmt, fmtTimer, num } from "../lib/format";

const props = defineProps({ workOrder: String });
const emit = defineEmits(["title", "actions"]);

const run = useRun(props.workOrder);
provide("run", run);

let poll = null;
onMounted(async () => {
	await run.refresh();
	emit("title", props.workOrder);
	emit("actions", [
		{ label: __("Open Work Order"), onClick: () => openForm("Work Order", props.workOrder) },
	]);
	poll = setInterval(() => isRunning.value && !run.busy.value && run.refresh(), 30000);
});
onBeforeUnmount(() => clearInterval(poll));

function openDesign() {
	const order = run.state.value.work_order;
	if (order.bom_creator) openForm("BOM Creator", order.bom_creator);
	else openForm("BOM", order.bom_no);
}

const STATUS = {
	"Not Started": "gray",
	"In Process": "blue",
	"On Hold": "amber",
	Breakdown: "red",
	Completed: "green",
};
const isRunning = computed(() => ["In Process", "Breakdown"].includes(run.status.value));

const view = computed(() => {
	const stages = run.stages.value;
	const modes = stages.map((s) => {
		if (s.breakdown) return "down";
		if (!["charging", "processing", "review"].includes(s.phase)) return "off";
		return run.paused.value ? "hold" : "run";
	});
	return {
		level: levels,
		mode: modes,
		working: modes.map((mode, i) => mode === "run" && stages[i].phase !== "charging"),
		flow: stages.map((s) => s.phase === "charging"),
		active: stages.map(run.isActive),
		storeActive: stages.some((s) => s.phase === "charging" && s.items.some((row) => !row.is_input)),
		fgActive: run.status.value === "Completed",
		cartons: levels.cartons ?? 0,
		crates: levels.crates ?? 1,
	};
});

const uoms = computed(() =>
	Object.fromEntries(
		(run.state.value?.stages || []).flatMap((s) => s.items.map((row) => [row.item_code, row.uom]))
	)
);

function holding(i) {
	const state = run.state.value;
	const stage = run.stages.value[i];
	if (stage.breakdown) return __("Breakdown");
	const weight = num(state.levels.machines[stage.workstation]);
	if (weight < 1) return __("Empty");
	const machine = machineOf(stage.machine_model);
	const item =
		stage.phase === "processing" || stage.phase === "review" ? __(machine.verb) : stage.output.item_name;
	return `${item} · ${fmt(Math.round(weight))} ${state.plan.weight_uom}`;
}

const live = computed(() => {
	const state = run.state.value;
	return {
		stock: (material) =>
			`${fmt(Math.round(num(state.levels.store[material.id])))} ${uoms.value[material.id] || ""}`,
		holding,
		packed: num(state.work_order.produced_qty),
	};
});
</script>

<template>
	<div v-if="run.state.value" class="flex min-h-0 flex-1 flex-col">
		<div class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-2 px-5">
			<Badge
				:label="__(run.status.value)"
				:theme="STATUS[run.status.value] || 'gray'"
				variant="subtle"
			/>
			<span class="min-w-0 truncate text-sm text-ink-gray-5">{{
				run.state.value.work_order.item_name
			}}</span>
			<div class="ml-auto flex shrink-0 items-center gap-2">
				<template v-if="run.status.value !== 'Not Started'">
					<Tooltip :text="__('Time on the Work Order, without holds')">
						<div class="flex h-7 items-center gap-1.5 rounded-4 bg-surface-gray-2 px-2">
							<span
								class="size-4"
								:class="
									isRunning
										? 'lucide-timer text-ink-gray-6'
										: 'lucide-timer-off text-ink-gray-5'
								"
								aria-hidden="true"
							/>
							<span class="w-[4.25rem] text-base font-medium tabular-nums text-ink-gray-8">{{
								fmtTimer(run.elapsed.value)
							}}</span>
						</div>
					</Tooltip>
					<Button
						v-if="isRunning"
						icon-left="lucide-pause"
						:label="__('Pause')"
						:disabled="!run.hasActiveStage.value || run.busy.value"
						@click="run.pause"
					/>
					<Button
						v-else-if="run.status.value === 'On Hold'"
						icon-left="lucide-play"
						:label="__('Resume')"
						@click="run.resume"
					/>
					<div class="mx-1 h-5 w-px bg-surface-gray-4" />
				</template>
				<Button
					variant="ghost"
					icon-left="lucide-settings-2"
					:label="__('Process Design')"
					@click="openDesign"
				/>
			</div>
		</div>
		<div class="flex min-h-0 flex-1">
			<div class="relative min-w-0 flex-1 bg-surface-gray-1">
				<PlantScene
					:plant="run.plant.value"
					:view="view"
					:live="live"
					:chip="run.activity.value"
					:paused="run.paused.value"
					@resume="run.resume"
				/>
			</div>
			<RunPanel class="w-[25rem] shrink-0 border-l border-outline-gray-2" />
		</div>
	</div>
</template>
