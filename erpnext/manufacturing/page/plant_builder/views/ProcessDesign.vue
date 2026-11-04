<script setup>
import { computed, onMounted, provide, ref, watch } from "vue";
import { ScrollArea, Switch } from "frappe-ui";
import PlantScene from "../components/three/PlantScene.vue";
import SetupStatus from "../components/setup/SetupStatus.vue";
import FormulaSection from "../components/setup/FormulaSection.vue";
import StagesSection from "../components/setup/StagesSection.vue";
import { __, call } from "../lib/api";
import { READ_ONLY, toScenePlant } from "../lib/plant";
import { designRows, fromDesign, rowsKey, toDesign } from "../lib/design";
import { previewView } from "../lib/scene";
import { num } from "../lib/format";

const props = defineProps({ design: Object, readOnly: Boolean });
const emit = defineEmits(["change"]);

const HEADER_FIELDS = ["item_code", "qty", "company", "raw_material_warehouse", "formula_tolerance"];

const catalog = ref(null);
const doc = ref(null);
const data = ref({ machines: {}, errors: [], item: null, weight_factors: {}, outputs: {}, items: {} });
const animate = ref(true);
const focus = ref(null);
const readOnly = computed(() => props.readOnly);
provide(READ_ONLY, readOnly);

let emittedKey = rowsKey(designRows(props.design));
let checkTimer = null;

const typeModels = computed(() =>
	Object.fromEntries((catalog.value || []).map((type) => [type.name, type.machine_model]))
);
const header = (design) => HEADER_FIELDS.map((field) => design[field] ?? "").join("|");

onMounted(async () => {
	catalog.value = (await call("get_machine_catalog")).workstation_types;
	doc.value = fromDesign(props.design, typeModels.value);
	check();
});

watch(
	() => [rowsKey(designRows(props.design)), header(props.design)],
	([incoming], [, before]) => {
		emittedKey = incoming;
		const local = doc.value && rowsKey(toDesign(doc.value));
		if (doc.value && (incoming !== local || header(props.design) !== before)) {
			doc.value = fromDesign(props.design, typeModels.value);
		}
		scheduleCheck();
	}
);

watch(
	doc,
	(value) => {
		if (!value) return;
		const rows = toDesign(value);
		const key = rowsKey(rows);
		if (key !== emittedKey) {
			emittedKey = key;
			emit("change", rows);
		}
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
		doc: { ...values, track_semi_finished_goods: 1, ...toDesign(doc.value) },
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
</script>

<template>
	<div v-if="doc" class="flex min-h-0 flex-1">
		<aside class="flex w-[32rem] shrink-0 flex-col border-r border-outline-gray-2">
			<ScrollArea class="min-h-0 flex-1" viewport-class="px-5 pt-5 pb-16">
				<fieldset :disabled="readOnly" class="m-0 min-w-0 space-y-8 border-0 p-0">
					<SetupStatus :errors="data.errors" />
					<FormulaSection :doc="doc" :data="data" :machines="data.machines" />
					<StagesSection
						:doc="doc"
						:machines="data.machines"
						:catalog="catalog"
						:outputs="data.outputs"
						:items="data.items"
						:focus="focus"
						@focus="focus = $event"
					/>
				</fieldset>
			</ScrollArea>
		</aside>
		<div class="relative min-w-0 flex-1 bg-surface-gray-1">
			<PlantScene :plant="scenePlant" :view="view">
				<template #overlay>
					<div class="w-80 rounded-5 border border-outline-gray-2 bg-surface-base p-4 shadow-sm">
						<p class="text-base-semibold text-ink-gray-8">{{ __("Built from your design") }}</p>
						<p class="mt-1 text-p-sm text-ink-gray-6">
							{{
								__(
									"Tanks, machines and pipes follow your formula and stages. Hover a stage on the left to find it here."
								)
							}}
						</p>
						<div class="mt-3">
							<Switch v-model="animate" :label="__('Animate Machines')" />
						</div>
					</div>
				</template>
			</PlantScene>
		</div>
	</div>
</template>
