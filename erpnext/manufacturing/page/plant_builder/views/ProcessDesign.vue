<script setup>
import { computed, onMounted, provide, ref, watch } from "vue";
import { Button, FormControl, ScrollArea, Tooltip } from "frappe-ui";
import PlantScene from "../components/three/PlantScene.vue";
import SetupStatus from "../components/setup/SetupStatus.vue";
import StagesSection from "../components/setup/StagesSection.vue";
import { __, call } from "../lib/api";
import { READ_ONLY, toScenePlant } from "../lib/plant";
import { designRows, fromDesign, rowsKey, toDesign } from "../lib/design";
import { previewView } from "../lib/scene";
import { num } from "../lib/format";

const props = defineProps({ design: Object, readOnly: Boolean });
const emit = defineEmits(["change", "update"]);

const HEADER_FIELDS = ["item_code", "qty", "raw_material_warehouse"];

const catalog = ref(null);
const doc = ref(null);
const data = ref({ machines: {}, errors: [], item: null, weight_factors: {}, outputs: {}, items: {} });
const animate = ref(true);
const focus = ref(null);
const readOnly = computed(() => props.readOnly);
provide(READ_ONLY, readOnly);

let emittedKey = null;
let checkTimer = null;

const typeModels = computed(() =>
	Object.fromEntries((catalog.value || []).map((type) => [type.name, type.machine_model]))
);
const header = (design) => HEADER_FIELDS.map((field) => design[field] ?? "").join("|");

function load() {
	doc.value = fromDesign(props.design, typeModels.value);
	emittedKey = rowsKey(toDesign(doc.value));
}

onMounted(async () => {
	catalog.value = (await call("get_machine_catalog")).workstation_types;
	load();
	check();
});

watch(
	() => [rowsKey(designRows(props.design)), header(props.design)],
	([incoming], [, before]) => {
		if (doc.value && (incoming !== emittedKey || header(props.design) !== before)) load();
		scheduleCheck();
	}
);

watch(
	doc,
	(value) => {
		const key = value && rowsKey(toDesign(value));
		if (!value || key === emittedKey || readOnly.value) return;
		emittedKey = key;
		emit("change", toDesign(value));
		scheduleCheck();
	},
	{ deep: true }
);

function scheduleCheck() {
	clearTimeout(checkTimer);
	checkTimer = setTimeout(check, 600);
}

async function check() {
	if (!doc.value) return;
	const values = Object.fromEntries(HEADER_FIELDS.map((field) => [field, props.design[field]]));
	const result = await call("check_design", {
		doc: { ...values, ...toDesign(doc.value) },
	});
	data.value = result;
	const balance = doc.value.materials.find((row) => row.is_balance_item);
	if (balance && result.balance_qty !== null && Math.abs(num(balance.qty) - result.balance_qty) > 0.0005) {
		balance.qty = result.balance_qty;
	}
}

const scenePlant = computed(() => {
	const items = data.value.items || {};
	const named = (rows) =>
		rows.map((row) => ({ ...row, item_name: items[row.item_code]?.item_name || row.item_code }));
	const factors = data.value.weight_factors || {};
	const materials = named(doc.value.materials).map((row) => ({
		...row,
		weight: num(row.qty) / (num(factors[row.item_code]) || 1),
	}));
	const total = materials.reduce((sum, row) => sum + row.weight, 0);
	return toScenePlant(
		{
			...doc.value,
			materials: materials.map((row) => ({
				...row,
				percentage: total ? (row.weight / total) * 100 : 0,
			})),
			packing_materials: named(doc.value.packing_materials),
		},
		data.value.machines,
		data.value.item
	);
});
const view = computed(() => previewView(scenePlant.value, animate.value, focus.value));

const batchKey = ref(0);
function setBatchSize(value) {
	if (num(value) > 0) emit("update", { qty: num(value) });
}
function restoreBatchSize(event) {
	if (num(event.target.value) <= 0) batchKey.value++;
}
</script>

<template>
	<div v-if="doc" class="flex min-h-0 flex-1">
		<aside class="flex w-[32rem] shrink-0 flex-col border-r border-outline-gray-2">
			<ScrollArea class="min-h-0 flex-1" viewport-class="px-5 pt-5 pb-16">
				<fieldset :disabled="readOnly" class="m-0 min-w-0 space-y-8 border-0 p-0">
					<div class="grid grid-cols-2 gap-3">
						<FormControl
							:key="batchKey"
							:model-value="design.qty"
							type="number"
							variant="outline"
							:label="__('Finished Good Quantity')"
							:debounce="500"
							@update:model-value="setBatchSize"
							@blur="restoreBatchSize"
						>
							<template v-if="data.item?.stock_uom" #suffix>
								<span class="text-xs text-ink-gray-5">{{ data.item.stock_uom }}</span>
							</template>
						</FormControl>
						<FormControl
							:model-value="design.formula_tolerance"
							type="number"
							variant="outline"
							:label="__('Formula Tolerance (%)')"
							:debounce="500"
							@update:model-value="emit('update', { formula_tolerance: num($event) })"
						/>
					</div>
					<SetupStatus :errors="data.errors" />
					<StagesSection
						:doc="doc"
						:machines="data.machines"
						:catalog="catalog"
						:outputs="data.outputs"
						:data="data"
						:focus="focus"
						@focus="focus = $event"
					/>
				</fieldset>
			</ScrollArea>
		</aside>
		<div class="relative min-w-0 flex-1 bg-surface-gray-1">
			<PlantScene :plant="scenePlant" :view="view">
				<template #tools>
					<Tooltip :text="animate ? __('Stop Machines') : __('Animate Machines')">
						<Button
							variant="ghost"
							:aria-label="animate ? __('Stop Machines') : __('Animate Machines')"
							:icon="animate ? 'lucide-pause' : 'lucide-play'"
							@click="animate = !animate"
						/>
					</Tooltip>
				</template>
			</PlantScene>
		</div>
	</div>
</template>
