<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Button, ScrollArea, Switch } from "frappe-ui";
import PlantScene from "../components/three/PlantScene.vue";
import SetupStatus from "../components/setup/SetupStatus.vue";
import ProductSection from "../components/setup/ProductSection.vue";
import FormulaSection from "../components/setup/FormulaSection.vue";
import StagesSection from "../components/setup/StagesSection.vue";
import { __, call, openList, setRoute } from "../lib/api";
import { newPlantDoc, toScenePlant } from "../lib/plant";
import { previewView } from "../lib/scene";

const props = defineProps({ name: String });
const emit = defineEmits(["title", "actions"]);

const doc = ref(null);
const saved = ref("");
const data = ref({ machines: {}, errors: [], item: null, is_saved: false });
const catalog = ref([]);
const saving = ref(false);
const animate = ref(true);
const focus = ref(null);
let checkTimer = null;

const dirty = computed(() => !!doc.value && JSON.stringify(doc.value) !== saved.value);

function apply(result) {
	data.value = result;
	doc.value = result.doc;
	saved.value = JSON.stringify(result.doc);
	emit("title", result.doc.floor_name || __("New Plant"));
}

onMounted(async () => {
	catalog.value = (await call("get_machine_catalog")).workstation_types;
	const result =
		props.name === "new"
			? await call("check_plant", { doc: newPlantDoc() })
			: await call("get_plant", { name: props.name });
	apply(result);
	if (props.name === "new") saved.value = "";
	emit(
		"actions",
		props.name === "new"
			? []
			: [
					{
						label: __("View Work Orders"),
						onClick: () => openList("Work Order", { plant_floor: props.name }),
					},
			  ]
	);
});

watch(
	doc,
	() => {
		if (!dirty.value) return;
		clearTimeout(checkTimer);
		checkTimer = setTimeout(check, 600);
	},
	{ deep: true }
);

async function check() {
	const result = await call("check_plant", { doc: doc.value });
	data.value = { ...result, is_saved: data.value.is_saved };
	syncNames(result.doc);
}

function syncNames(checked) {
	["materials", "packing_materials"].forEach((table) =>
		(checked[table] || []).forEach((row, i) => {
			const local = doc.value[table][i];
			if (local && local.item_code === row.item_code && local.item_name !== row.item_name) {
				local.item_name = row.item_name;
			}
		})
	);
}

async function save() {
	saving.value = true;
	try {
		clearTimeout(checkTimer);
		const result = await call("save_plant", { doc: doc.value });
		apply(result);
		if (props.name === "new") setRoute(result.doc.name);
	} finally {
		saving.value = false;
	}
}

async function runWorkOrder() {
	const workOrder = await call("make_work_order", { plant_floor: doc.value.name });
	setRoute(doc.value.name, workOrder);
}

const scenePlant = computed(() => toScenePlant(doc.value, data.value.machines, data.value.item));
const view = computed(() => previewView(scenePlant.value, animate.value, focus.value));
const canRun = computed(() => data.value.is_saved && !dirty.value && !data.value.errors.length);
</script>

<template>
	<div v-if="doc" class="flex min-h-0 flex-1 flex-col">
		<div class="flex h-12 shrink-0 items-center justify-end gap-2 border-b border-outline-gray-2 px-5">
			<Button
				:variant="dirty ? 'solid' : 'subtle'"
				icon-left="lucide-save"
				:label="__('Save')"
				:loading="saving"
				:disabled="!dirty"
				@click="save"
			/>
			<Button
				:variant="dirty ? 'subtle' : 'solid'"
				icon-left="lucide-play"
				:label="__('Run a Work Order')"
				:disabled="!canRun"
				@click="runWorkOrder"
			/>
		</div>
		<div class="flex min-h-0 flex-1">
			<aside class="flex w-[30rem] shrink-0 flex-col border-r border-outline-gray-2">
				<ScrollArea class="min-h-0 flex-1" viewport-class="px-5 pt-5 pb-16">
					<div class="space-y-8">
						<SetupStatus :errors="data.errors" />
						<ProductSection :doc="doc" :item="data.item" :is-saved="data.is_saved" />
						<FormulaSection :doc="doc" :machines="data.machines" />
						<StagesSection
							:doc="doc"
							:machines="data.machines"
							:catalog="catalog"
							:focus="focus"
							@focus="focus = $event"
						/>
					</div>
				</ScrollArea>
			</aside>
			<div class="relative min-w-0 flex-1 bg-surface-gray-1">
				<PlantScene :plant="scenePlant" :view="view">
					<template #overlay>
						<div
							class="w-80 rounded-5 border border-outline-gray-2 bg-surface-base p-4 shadow-sm"
						>
							<p class="text-base-semibold text-ink-gray-8">
								{{ __("Built from your setup") }}
							</p>
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
	</div>
</template>
