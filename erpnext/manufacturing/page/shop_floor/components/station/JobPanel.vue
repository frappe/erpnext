<script setup>
import { computed, ref } from "vue";
import { Avatar, Badge, Button } from "frappe-ui";
import CrewDialog from "./CrewDialog.vue";
import ReasonDialog from "./ReasonDialog.vue";
import QualityDialog from "./QualityDialog.vue";
import StepReady from "./StepReady.vue";
import StepPieces from "./StepPieces.vue";
import ProcessStage from "./ProcessStage.vue";
import { __, call, notify, openForm } from "../../lib/api";
import { fmtDuration } from "../../lib/format";
import { isManager, session } from "../../lib/session";
import { phaseOf } from "../../lib/status";

const PAUSE_REASONS = [
	"Break",
	"Waiting for material",
	"Waiting for quality check",
	"Cleaning",
	"Shift handover",
];

const props = defineProps({ station: Object, jobCard: Object, busy: Boolean });
const emit = defineEmits(["changed"]);

const working = ref(false);
const crewOpen = ref(false);
const crewMode = ref("start");
const pauseOpen = ref(false);
const qualityOpen = ref(false);

const active = computed(() => ["running", "paused"].includes(props.jobCard.phase));
const phase = computed(() => phaseOf(props.jobCard));
const steps = [__("Start"), __("Log quantities"), __("Complete")];
const stepIndex = computed(() => (active.value ? 1 : props.jobCard.phase === "done" ? 2 : 0));
const blocked = computed(() => {
	if (props.station.workstation.status === "Problem")
		return __("Restart the machine before you start a job.");
	if (props.busy)
		return __("{0} is busy with another job card. Start when it is free.", [
			props.station.workstation.name,
		]);
	if (!props.jobCard.ready_qty) return __("Nothing is ready from the previous operation yet.");
	return "";
});

async function act(method, args, message) {
	working.value = true;
	try {
		await call(method, { job_card: props.jobCard.name, employee: session.employee.name, ...args });
		if (message) notify(message);
		emit("changed");
	} finally {
		working.value = false;
	}
}

function openCrew(mode) {
	crewMode.value = mode;
	crewOpen.value = true;
}

function onCrew(employees) {
	if (crewMode.value === "assign") return act("assign_job_card", { employees }, __("Job Card assigned"));
	if (crewMode.value === "start") return act("start_job", { employees }, __("Job started"));
	return act("change_crew", { employees }, __("Crew updated"));
}

const logQty = (args) => act("log_progress", args);

function complete() {
	if (props.jobCard.quality_required) return (qualityOpen.value = true);
	return act("complete_job", {}, __("Job Card {0} completed", [props.jobCard.name]));
}
</script>

<template>
	<section class="rounded-6 border border-outline-gray-2 bg-surface-base shadow-sm">
		<div class="flex flex-wrap items-start gap-3 border-b border-outline-gray-1 p-5">
			<div class="min-w-0 flex-1">
				<p class="text-sm text-ink-gray-5">{{ active ? __("Current job") : __("Next up") }}</p>
				<h2 class="mt-1 truncate text-3xl font-semibold text-ink-gray-9">
					{{ jobCard.operation }} · {{ jobCard.item_name || jobCard.production_item }}
				</h2>
				<button
					type="button"
					class="mt-1 truncate text-sm tabular-nums text-ink-gray-5 hover:underline"
					@click="openForm('Job Card', jobCard.name)"
				>
					{{ jobCard.name }} · {{ jobCard.work_order }}
				</button>
			</div>
			<div class="flex flex-col items-end gap-2">
				<Badge :label="phase.label" :theme="phase.theme" variant="subtle" size="lg" />
				<Button
					v-if="isManager"
					variant="ghost"
					icon-left="lucide-user-plus"
					:label="jobCard.assigned.length ? __('Reassign') : __('Assign')"
					@click="openCrew('assign')"
				/>
			</div>
		</div>

		<template v-if="!jobCard.is_process">
			<ol class="grid grid-cols-3 gap-2 px-5 pt-4" :aria-label="__('Job steps')">
				<li v-for="(label, i) in steps" :key="label" class="space-y-1.5">
					<div
						class="h-1.5 rounded-full"
						:class="
							i < stepIndex
								? 'bg-surface-green-7'
								: i === stepIndex
								? 'bg-surface-gray-7'
								: 'bg-surface-gray-3'
						"
					/>
					<p
						class="truncate text-sm"
						:class="i === stepIndex ? 'font-medium text-ink-gray-9' : 'text-ink-gray-5'"
						:aria-current="i === stepIndex ? 'step' : undefined"
					>
						{{ label }}
					</p>
				</li>
			</ol>

			<div v-if="active" class="flex flex-wrap items-center gap-3 px-5 pt-4">
				<div class="flex -space-x-1.5">
					<Avatar v-for="id in jobCard.crew" :key="id" :label="jobCard.names[id] || id" size="lg" />
				</div>
				<div class="min-w-0 flex-1">
					<p class="truncate text-base text-ink-gray-8">
						{{
							jobCard.phase === "paused"
								? __("Paused. Resume to continue logging time.")
								: jobCard.crew.map((id) => jobCard.names[id] || id).join(", ")
						}}
					</p>
					<p class="text-sm tabular-nums text-ink-gray-5">
						{{ __("{0} logged on this job", [fmtDuration(jobCard.worked_seconds)]) }}
					</p>
				</div>
				<template v-if="station.workstation.status !== 'Problem'">
					<Button
						v-if="jobCard.phase === 'running'"
						size="lg"
						variant="subtle"
						icon-left="lucide-users"
						:label="__('Change Crew')"
						@click="openCrew('change')"
					/>
					<Button
						v-if="jobCard.phase === 'paused'"
						size="lg"
						variant="solid"
						icon-left="lucide-play"
						:label="__('Resume')"
						:loading="working"
						@click="act('resume_job', {}, __('Job resumed'))"
					/>
					<Button
						v-else
						size="lg"
						variant="subtle"
						icon-left="lucide-pause"
						:label="__('Pause')"
						@click="pauseOpen = true"
					/>
				</template>
			</div>

			<div class="p-5">
				<StepPieces
					v-if="active || jobCard.phase === 'done'"
					:job-card="jobCard"
					:busy="working"
					@log="logQty"
					@complete="complete"
				/>
				<StepReady v-else :job-card="jobCard" :blocked="blocked" @start="openCrew('start')" />
			</div>
		</template>
		<div v-else class="p-5">
			<ProcessStage :job-card="jobCard" />
		</div>

		<CrewDialog v-model:open="crewOpen" :job-card="jobCard" :mode="crewMode" @confirm="onCrew" />
		<ReasonDialog
			v-model:open="pauseOpen"
			:title="__('Why are you pausing?')"
			:hint="__('The timer stops until you resume. For a machine fault, use Report Breakdown instead.')"
			:reasons="PAUSE_REASONS"
			:action="__('Pause Job')"
			@confirm="(reason) => act('pause_job', { reason }, __('Job paused'))"
		/>
		<QualityDialog
			v-model:open="qualityOpen"
			:job-card="jobCard"
			@done="act('complete_job', {}, __('Job Card {0} completed', [jobCard.name]))"
		/>
	</section>
</template>
