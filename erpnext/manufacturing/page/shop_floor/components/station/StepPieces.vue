<script setup>
import { computed, ref, watch } from "vue";
import { Avatar, Button, Progress, TabButtons } from "frappe-ui";
import NumberStepper from "./NumberStepper.vue";
import ReasonDialog from "./ReasonDialog.vue";
import { __ } from "../../lib/api";
import { fmt, num } from "../../lib/format";
import { session } from "../../lib/session";

const props = defineProps({ jobCard: Object, busy: Boolean });
const emit = defineEmits(["log", "complete"]);

const qty = ref(1);
const lossOpen = ref(false);
const who = ref(
	props.jobCard.crew.includes(session.employee.name) ? session.employee.name : props.jobCard.crew[0]
);
watch(
	() => props.jobCard.crew,
	(crew) => !crew.includes(who.value) && (who.value = crew[0])
);

const stopped = computed(() => props.jobCard.phase !== "running");
const available = computed(() =>
	Math.max(0, Math.min(num(props.jobCard.ready_qty), num(props.jobCard.left_qty)))
);
const counts = computed(() => [
	{ label: __("Done"), value: props.jobCard.total_completed_qty, tone: "text-ink-gray-9" },
	{
		label: __("Lost"),
		value: props.jobCard.process_loss_qty,
		tone: props.jobCard.process_loss_qty ? "text-ink-red-5" : "text-ink-gray-9",
	},
	{ label: __("Left to do"), value: props.jobCard.left_qty, tone: "text-ink-gray-9" },
]);
const quick = computed(() => [...new Set([1, 5, 10].filter((n) => n <= available.value))]);
const qtyError = computed(() => num(qty.value) <= 0 || num(qty.value) > available.value);

const log = (completed) => emit("log", { employee: who.value, completed_qty: completed });
const logLoss = (reason, lost) =>
	emit("log", { employee: who.value, process_loss_qty: lost, loss_reason: reason });
</script>

<template>
	<div class="space-y-5">
		<div class="rounded-5 bg-surface-gray-1 p-5">
			<div class="grid grid-cols-3 gap-4">
				<div v-for="count in counts" :key="count.label">
					<p class="text-sm text-ink-gray-5">{{ count.label }}</p>
					<p
						class="mt-1 text-[2.25rem] font-semibold leading-none tabular-nums"
						:class="count.tone"
					>
						{{ fmt(count.value) }}
					</p>
				</div>
			</div>
			<Progress
				:value="(jobCard.total_completed_qty / jobCard.for_quantity) * 100"
				size="lg"
				class="mt-4"
			/>
			<p class="mt-3 text-sm text-ink-gray-6">
				{{ __("{0} {1} ready to work on", [fmt(available), jobCard.stock_uom]) }}
				<template v-if="available < jobCard.left_qty">
					· {{ __("the rest is still with the previous operation") }}</template
				>
			</p>
		</div>

		<div v-if="jobCard.crew.length > 1" class="space-y-1.5">
			<p class="text-sm text-ink-gray-6">{{ __("Adding for") }}</p>
			<TabButtons
				v-model="who"
				:options="jobCard.crew.map((id) => ({ label: jobCard.names[id] || id, value: id }))"
			/>
		</div>

		<div class="flex flex-wrap items-end gap-2">
			<Button
				v-for="n in quick"
				:key="n"
				size="lg"
				variant="subtle"
				class="h-12 min-w-20 text-lg"
				:label="`+${n}`"
				:disabled="stopped || busy"
				@click="log(n)"
			/>
			<div class="ml-auto flex items-end gap-2">
				<NumberStepper
					v-model="qty"
					:label="__('Quantity')"
					:invalid="qtyError"
					:disabled="stopped"
				/>
				<Button
					size="lg"
					variant="solid"
					icon-left="lucide-circle-check"
					:label="__('Add to Done')"
					:disabled="stopped || busy || qtyError"
					@click="log(num(qty))"
				/>
			</div>
		</div>

		<div class="flex flex-wrap gap-2">
			<Button
				size="lg"
				variant="outline"
				theme="red"
				icon-left="lucide-circle-x"
				:label="__('Add to Lost')"
				:disabled="stopped || busy || available < 1"
				@click="lossOpen = true"
			/>
			<Button
				size="lg"
				:variant="jobCard.left_qty ? 'subtle' : 'solid'"
				icon-left="lucide-flag"
				class="ml-auto"
				:label="jobCard.left_qty ? __('{0} left', [fmt(jobCard.left_qty)]) : __('Complete Job Card')"
				:disabled="!!jobCard.left_qty || busy"
				@click="$emit('complete')"
			/>
		</div>

		<div v-if="jobCard.pieces.length" class="space-y-2">
			<p class="text-sm text-ink-gray-6">{{ __("By operator") }}</p>
			<div v-for="row in jobCard.pieces" :key="row.employee" class="flex items-center gap-2 text-base">
				<Avatar :label="row.employee_name || row.employee" size="sm" />
				<span class="min-w-0 flex-1 truncate text-ink-gray-8">{{
					row.employee_name || row.employee
				}}</span>
				<span class="tabular-nums text-ink-gray-7">{{
					__("{0} done · {1} lost", [fmt(row.completed_qty), fmt(row.process_loss_qty)])
				}}</span>
			</div>
		</div>

		<ReasonDialog
			v-model:open="lossOpen"
			:title="__('Lost Quantity')"
			:hint="__('Rejected or scrapped quantity. It counts as process loss on the Job Card.')"
			:reasons="jobCard.loss_reasons"
			with-qty
			:max-qty="available"
			:action="__('Add to Lost')"
			theme="red"
			@confirm="logLoss"
		/>
	</div>
</template>
