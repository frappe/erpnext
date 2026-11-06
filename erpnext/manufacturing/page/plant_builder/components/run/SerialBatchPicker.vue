<script setup>
import { computed, inject, ref, watch } from "vue";
import { Button, Checkbox, Dialog, TextInput } from "frappe-ui";
import { __ } from "../../lib/api";
import { fmt, num, round } from "../../lib/format";

const SHOWN_SERIAL_NOS = 200;

const props = defineProps({ stage: Object, row: Object });
const open = defineModel("open", { type: Boolean, default: false });
const run = inject("run");

const options = ref(null);
const batches = ref({});
const serialNos = ref([]);
const search = ref("");

const isSerial = computed(() => !!props.row.has_serial_no);
const needed = computed(() => round(run.usedOf(props.stage, props.row), 3));
const picked = computed(() =>
	round(
		isSerial.value
			? serialNos.value.length
			: Object.values(batches.value).reduce((a, b) => a + num(b), 0),
		3
	)
);
const overdrawn = computed(() =>
	(options.value?.batches || []).filter((row) => num(batches.value[row.batch_no]) > row.qty)
);
const filtered = computed(() => {
	const text = search.value.trim().toLowerCase();
	const rows = options.value?.serial_nos || [];
	return (text ? rows.filter((row) => row.serial_no.toLowerCase().includes(text)) : rows).slice(
		0,
		SHOWN_SERIAL_NOS
	);
});

watch(
	open,
	async (value) => {
		if (!value) return;
		const pick = run.pickOf(props.stage, props.row);
		batches.value = { ...(pick?.batches || {}) };
		serialNos.value = [...(pick?.serial_nos || [])];
		search.value = "";
		options.value = null;
		options.value = await run.getPickOptions(props.stage, props.row);
	},
	{ immediate: true }
);

function fillInOrder() {
	let left = needed.value;
	if (isSerial.value) {
		serialNos.value = options.value.serial_nos
			.slice(0, Math.max(0, Math.round(left)))
			.map((row) => row.serial_no);
		return;
	}
	batches.value = {};
	for (const row of options.value.batches) {
		if (left <= 0) break;
		batches.value[row.batch_no] = round(Math.min(row.qty, left), 3);
		left = round(left - row.qty, 3);
	}
}

function toggle(serialNo, on) {
	serialNos.value = on
		? [...serialNos.value, serialNo]
		: serialNos.value.filter((name) => name !== serialNo);
}

function apply() {
	if (isSerial.value) {
		run.setPick(props.stage, props.row, { serial_nos: serialNos.value, label: summary(serialNos.value) });
	} else {
		const chosen = Object.fromEntries(Object.entries(batches.value).filter(([, qty]) => num(qty) > 0));
		const names = options.value.batches.filter((row) => chosen[row.batch_no]).map((row) => row.batch_id);
		run.setPick(props.stage, props.row, { batches: chosen, label: names.join(", ") });
	}
	open.value = false;
}

function clear() {
	run.setPick(props.stage, props.row, null);
	open.value = false;
}

const dateOf = (value) => (value ? window.frappe.datetime.str_to_user(value) : "");
const summary = (names) => (names.length === 1 ? names[0] : __("{0} serial nos", [names.length]));
</script>

<template>
	<Dialog v-model:open="open" size="xl" :title="isSerial ? __('Pick Serial Nos') : __('Pick Batches')">
		<div
			class="space-y-3 [&_input[type=number]::-webkit-inner-spin-button]:appearance-none [&_input[type=number]::-webkit-outer-spin-button]:appearance-none [&_input[type=number]]:[appearance:textfield]"
		>
			<p class="text-p-sm text-ink-gray-6">
				{{ __("{0} from {1}", [row.item_name, row.source_warehouse]) }}
			</p>
			<p v-if="!options" class="text-p-sm text-ink-gray-5">{{ __("Loading...") }}</p>
			<p
				v-else-if="!(isSerial ? options.serial_nos : options.batches)?.length"
				class="text-p-sm text-ink-gray-5"
			>
				{{ isSerial ? __("No serial nos are in stock here.") : __("No batches are in stock here.") }}
			</p>
			<template v-else-if="isSerial">
				<TextInput v-model="search" :placeholder="__('Search serial no')" variant="outline" />
				<div
					class="max-h-80 divide-y divide-outline-gray-1 overflow-y-auto rounded-4 border border-outline-gray-2"
				>
					<label
						v-for="row in filtered"
						:key="row.serial_no"
						class="flex h-9 cursor-pointer items-center gap-2 px-3"
					>
						<Checkbox
							:model-value="serialNos.includes(row.serial_no)"
							@update:model-value="toggle(row.serial_no, $event)"
						/>
						<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-8">{{
							row.serial_no
						}}</span>
						<span v-if="row.batch_no" class="shrink-0 text-xs text-ink-gray-5">{{
							row.batch_no
						}}</span>
					</label>
				</div>
				<p v-if="filtered.length === SHOWN_SERIAL_NOS" class="text-xs text-ink-gray-5">
					{{ __("Showing the first {0}. Search to find others.", [SHOWN_SERIAL_NOS]) }}
				</p>
			</template>
			<div v-else class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
				<div
					class="grid h-8 grid-cols-[minmax(0,1fr)_6rem_6rem_7rem] items-center gap-2 px-3 text-xs text-ink-gray-5"
				>
					<span>{{ __("Batch") }}</span>
					<span>{{ __("Expiry") }}</span>
					<span class="text-right">{{ __("In Stock") }}</span>
					<span class="text-right">{{ __("Pick") }}</span>
				</div>
				<div
					v-for="option in options.batches"
					:key="option.batch_no"
					class="grid h-11 grid-cols-[minmax(0,1fr)_6rem_6rem_7rem] items-center gap-2 px-3"
				>
					<span class="truncate text-sm text-ink-gray-8">{{
						option.batch_id || option.batch_no
					}}</span>
					<span class="truncate text-sm text-ink-gray-6">
						{{ dateOf(option.expiry_date) }}
					</span>
					<span class="text-right text-sm tabular-nums text-ink-gray-6">{{ fmt(option.qty) }}</span>
					<TextInput
						v-model="batches[option.batch_no]"
						type="number"
						size="sm"
						class="[&_input]:bg-surface-base [&_input]:text-right"
						:class="num(batches[option.batch_no]) > option.qty ? '[&_input]:text-ink-red-5' : ''"
					/>
				</div>
			</div>
			<p
				v-if="options"
				class="text-p-sm"
				:class="picked === needed ? 'text-ink-gray-6' : 'text-ink-amber-5'"
			>
				{{ __("Picked {0} of {1} {2}", [fmt(picked), fmt(needed), row.uom]) }}
			</p>
		</div>
		<template #actions>
			<div class="flex items-center gap-2">
				<Button
					:label="isSerial ? __('Pick First {0}', [fmt(needed)]) : __('Fill in Order')"
					:disabled="!options"
					@click="fillInOrder"
				/>
				<Button v-if="run.pickOf(stage, row)" :label="__('Pick Automatically')" @click="clear" />
				<Button
					variant="solid"
					class="ml-auto"
					:label="__('Use Picked')"
					:disabled="!options || !picked || overdrawn.length > 0"
					@click="apply"
				/>
			</div>
		</template>
	</Dialog>
</template>
