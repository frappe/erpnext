<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Badge, Button, Tooltip } from "frappe-ui";
import JobPanel from "../components/station/JobPanel.vue";
import QueueList from "../components/station/QueueList.vue";
import ActivityList from "../components/station/ActivityList.vue";
import RestartDialog from "../components/station/RestartDialog.vue";
import LoadFailed from "../../plant_builder/components/LoadFailed.vue";
import { __, call, go, notify } from "../lib/api";
import { timeOf } from "../lib/format";
import { isManager, session, usePolling } from "../lib/session";
import { STATION_THEME } from "../lib/status";

const props = defineProps({ workstation: String });

const station = ref(null);
const failed = ref(false);
const restartOpen = ref(false);
const working = ref(false);

async function load() {
	try {
		station.value = await call("get_station", {
			workstation: props.workstation,
			employee: session.employee.name,
		});
		failed.value = false;
	} catch {
		failed.value = !station.value;
	}
}

const polling = usePolling(load);
onMounted(() => {
	load();
	polling.start();
});
onBeforeUnmount(polling.stop);

const info = computed(() => station.value?.workstation);
const oee = computed(() => station.value?.oee);
const canReportBreakdown = computed(
	() => info.value?.status !== "Problem" && station.value?.job_card?.phase === "running"
);

async function reportBreakdown() {
	window.frappe.confirm(
		__("Stop {0} for a breakdown? Its running job is paused until you restart the machine.", [
			info.value.name,
		]),
		async () => {
			working.value = true;
			try {
				await call("report_breakdown", { workstation: info.value.name });
				notify(__("{0} stopped for a breakdown", [info.value.name]), "red");
				await load();
			} finally {
				working.value = false;
			}
		}
	);
}

async function restart(stopReason, remarks) {
	const downtime = await call("restart_machine", {
		workstation: info.value.name,
		stop_reason: stopReason,
		operator: session.employee.name,
		remarks,
	});
	notify(__("Machine restarted · {0} created", [downtime]));
	await load();
}
</script>

<template>
	<LoadFailed v-if="failed" @retry="load" />
	<div v-else-if="station" class="mx-auto max-w-[1280px] space-y-5 px-3 pt-5 pb-16 sm:px-5">
		<div class="flex flex-wrap items-center gap-3">
			<Button
				variant="ghost"
				icon="lucide-arrow-left"
				:aria-label="__('Back to the plant floor')"
				@click="go()"
			/>
			<h1 class="text-2xl font-semibold text-ink-gray-9">{{ info.name }}</h1>
			<Badge
				:label="__(info.status)"
				:theme="STATION_THEME[info.status] || 'gray'"
				variant="subtle"
				size="lg"
			/>
			<span v-if="info.warehouse" class="hidden text-sm text-ink-gray-5 sm:inline">{{
				info.warehouse
			}}</span>
			<Tooltip
				v-if="oee && oee.oee !== null"
				:text="
					__('Availability {0}% · Performance {1}% · Quality {2}%', [
						oee.availability,
						oee.performance,
						oee.quality,
					])
				"
			>
				<span class="rounded-4 bg-surface-gray-2 px-2 py-1 text-sm tabular-nums text-ink-gray-7">{{
					__("OEE {0}%", [oee.oee])
				}}</span>
			</Tooltip>
			<Button
				v-if="canReportBreakdown"
				class="ml-auto"
				size="lg"
				variant="outline"
				theme="red"
				icon-left="lucide-triangle-alert"
				:label="__('Report Breakdown')"
				:loading="working"
				@click="reportBreakdown"
			/>
		</div>

		<div
			v-if="info.status === 'Problem'"
			class="flex flex-wrap items-center gap-4 rounded-6 bg-surface-red-2 p-5"
		>
			<span class="lucide-octagon-x size-8 shrink-0 text-ink-red-5" aria-hidden="true" />
			<div class="min-w-0 flex-1">
				<p class="text-xl font-semibold text-ink-gray-9">
					{{ __("{0} is stopped for a breakdown", [info.name]) }}
				</p>
				<p v-if="info.breakdown" class="mt-0.5 text-p-base text-ink-gray-7">
					{{ __("Stopped at {0} on {1}.", [timeOf(info.breakdown.to_time), info.breakdown.name]) }}
				</p>
			</div>
			<Button
				size="lg"
				variant="solid"
				icon-left="lucide-rotate-cw"
				:label="__('Restart Machine')"
				@click="restartOpen = true"
			/>
		</div>

		<div v-if="station.busy" class="flex items-center gap-3 rounded-5 bg-surface-gray-2 px-4 py-3">
			<span class="lucide-lock size-5 shrink-0 text-ink-gray-5" aria-hidden="true" />
			<p class="text-base text-ink-gray-7">
				{{ __("{0} is running a job card assigned to someone else.", [info.name]) }}
			</p>
		</div>

		<div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
			<JobPanel
				v-if="station.job_card"
				:key="station.job_card.name"
				:station="station"
				:job-card="station.job_card"
				:busy="station.busy"
				@changed="load"
			/>
			<section
				v-else
				class="flex flex-col items-center justify-center gap-3 rounded-6 border border-outline-gray-2 py-20 text-center"
			>
				<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
					<span class="lucide-clipboard-list block size-6" aria-hidden="true" />
				</div>
				<p class="text-lg text-ink-gray-7">
					{{
						isManager
							? __("No open job cards on {0}", [info.name])
							: __("No job cards assigned to you on {0}", [info.name])
					}}
				</p>
				<Button size="lg" class="mt-2" :label="__('Back to the plant floor')" @click="go()" />
			</section>
			<aside class="space-y-6">
				<QueueList
					:title="__('Up Next')"
					:job-cards="station.queue"
					:empty="__('No other job cards for you here')"
				/>
				<QueueList
					v-if="station.done.length"
					:title="__('Completed Today')"
					:job-cards="station.done"
				/>
				<ActivityList
					v-if="station.activity.logs"
					:activity="station.activity"
					:names="station.activity.names"
				/>
			</aside>
		</div>

		<RestartDialog v-model:open="restartOpen" :workstation="info" @confirm="restart" />
	</div>
</template>
