<script setup>
import { computed, inject, reactive } from "vue";
import { Button, FormControl } from "frappe-ui";
import DeskControl from "../DeskControl.vue";
import { __ } from "../../lib/api";
import { fmtTimer } from "../../lib/format";

const props = defineProps({ stage: Object });
const run = inject("run");

const defaults = computed(() => run.state.value.downtime);
const reasons = computed(() => defaults.value.stop_reasons.map((value) => ({ label: __(value), value })));
const form = reactive({
	stop_reason: defaults.value.stop_reasons.includes("Machine malfunction") ? "Machine malfunction" : "",
	operator: defaults.value.operator || "",
	remarks: "",
});

const since = computed(() => props.stage.breakdown.since);
const stoppedAt = computed(() => window.frappe.datetime.str_to_user(since.value));
const downFor = computed(() => fmtTimer(Math.floor(run.secondsSince(since.value))));
const canRestart = computed(() => form.stop_reason && form.operator && !run.paused.value);
</script>

<template>
	<div class="space-y-4 rounded-4 border border-outline-red-3 p-3">
		<div class="flex items-start gap-2">
			<span class="lucide-octagon-x mt-0.5 size-4 shrink-0 text-ink-red-5" aria-hidden="true" />
			<div class="min-w-0 flex-1">
				<p class="text-base font-medium text-ink-gray-8">
					{{ __("{0} is down", [stage.workstation]) }}
				</p>
				<p class="text-p-sm text-ink-gray-6">
					{{
						__("Stopped at {0}. Record why it stopped, then restart it once it is fixed.", [
							stoppedAt,
						])
					}}
				</p>
			</div>
			<span class="shrink-0 text-sm tabular-nums text-ink-red-5">{{ downFor }}</span>
		</div>
		<div class="space-y-3">
			<DeskControl
				v-model="form.stop_reason"
				fieldtype="Select"
				:options="reasons"
				:label="__('Stop Reason')"
			/>
			<DeskControl
				v-model="form.operator"
				options="Employee"
				:label="__('Operator')"
				:filters="{ status: 'Active' }"
			/>
		</div>
		<FormControl
			v-model="form.remarks"
			type="textarea"
			:label="__('Remarks')"
			:placeholder="__('What broke and how it was fixed')"
		/>
		<Button
			variant="solid"
			icon-left="lucide-rotate-ccw"
			:label="__('Restart Machine')"
			class="w-full"
			:disabled="!canRestart"
			:loading="run.busy.value"
			@click="run.restartMachine(stage, { ...form })"
		/>
		<p class="text-p-xs text-ink-gray-5">
			{{ __("Restarting makes a Downtime Entry for the time the machine was down.") }}
		</p>
	</div>
</template>
