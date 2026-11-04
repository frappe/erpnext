<script setup>
import { computed, onBeforeUnmount, onMounted, provide, ref, watch } from "vue";
import { Badge, Button, FormControl, ScrollArea, Tooltip } from "frappe-ui";
import PlantScene from "../components/three/PlantScene.vue";
import SectionHead from "../components/setup/SectionHead.vue";
import DeskControl from "../components/DeskControl.vue";
import { __, call, openForm, openList, setRoute } from "../lib/api";
import { READ_ONLY } from "../lib/plant";
import { MACHINE_STATUS, floorView, newFloorDoc, toSceneFloor } from "../lib/floor";
import { machineOf } from "../lib/machines";
import { fmt } from "../lib/format";

const props = defineProps({ name: String });
const emit = defineEmits(["title", "actions"]);

const FIELDS = ["floor_name", "company", "warehouse"];
const isNew = props.name === "new";

const data = ref(null);
const doc = ref(null);
const saved = ref("");
const saving = ref(false);
const adding = ref("");
const focus = ref(null);
let poll = null;

const values = () => Object.fromEntries(FIELDS.map((field) => [field, doc.value[field] || ""]));
const dirty = computed(() => !!doc.value && JSON.stringify(values()) !== saved.value);
const readOnly = computed(() => !data.value?.can_write);
provide(READ_ONLY, readOnly);

function apply(result) {
	data.value = result;
	doc.value = { ...result.doc };
	saved.value = JSON.stringify(values());
	emit("title", result.doc.floor_name || __("New Plant Floor"));
}

onMounted(async () => {
	apply(
		isNew
			? {
					doc: newFloorDoc(),
					can_write: window.frappe.model.can_create("Plant Floor"),
					machines: [],
					work_orders: [],
			  }
			: await call("get_floor", { name: props.name })
	);
	if (isNew) saved.value = "";
	emit(
		"actions",
		isNew
			? []
			: [
					{
						label: __("View Machines"),
						onClick: () => openList("Workstation", { plant_floor: props.name }),
					},
			  ]
	);
	if (!isNew) poll = setInterval(refresh, 30000);
});
onBeforeUnmount(() => clearInterval(poll));

async function refresh() {
	if (dirty.value || saving.value) return;
	apply(await call("get_floor", { name: props.name }));
}

async function save() {
	saving.value = true;
	try {
		const result = await call("save_floor", { doc: { ...values(), name: isNew ? null : props.name } });
		apply(result);
		if (isNew) setRoute(result.doc.name);
	} finally {
		saving.value = false;
	}
}

async function setFloor(workstation, floor) {
	apply(await call("set_machine_floor", { workstation, plant_floor: floor }));
}

watch(adding, async (workstation) => {
	if (!workstation) return;
	await setFloor(workstation, props.name);
	adding.value = "";
});

const machines = computed(() => data.value?.machines || []);
const warehouseFilters = computed(() => ({ company: doc.value.company, is_group: 0 }));
const machineFilters = computed(() => ({ disabled: 0, plant_floor: ["!=", props.name] }));
const statusOf = (machine) => MACHINE_STATUS[machine.status] || MACHINE_STATUS.Off;

const scenePlant = computed(() => toSceneFloor(doc.value, machines.value));
const view = computed(() => floorView(machines.value, focus.value));
const live = computed(() => ({
	holding: (i) => {
		const machine = machines.value[i];
		const status = __(machine.status || "Off");
		return machine.job ? `${status} · ${machine.job.work_order}` : status;
	},
}));
</script>

<template>
	<div v-if="doc" class="flex min-h-0 flex-1 flex-col">
		<div class="flex h-12 shrink-0 items-center justify-end gap-2 border-b border-outline-gray-2 px-5">
			<Button
				v-if="!readOnly"
				:variant="dirty ? 'solid' : 'subtle'"
				icon-left="lucide-save"
				:label="__('Save')"
				:loading="saving"
				:disabled="!dirty"
				@click="save"
			/>
		</div>
		<div class="flex min-h-0 flex-1">
			<aside class="flex w-[30rem] shrink-0 flex-col border-r border-outline-gray-2">
				<ScrollArea class="min-h-0 flex-1" viewport-class="px-5 pt-5 pb-16">
					<fieldset :disabled="readOnly" class="m-0 min-w-0 space-y-8 border-0 p-0">
						<p v-if="readOnly" class="text-p-sm text-ink-gray-6">
							{{ __("You can view this floor but not change it.") }}
						</p>
						<section class="space-y-4">
							<SectionHead
								:title="__('Floor')"
								:description="
									__('Where the machines stand, and the main store of the floor.')
								"
							/>
							<div class="grid grid-cols-2 gap-3">
								<FormControl
									v-model="doc.floor_name"
									:label="__('Floor Name')"
									:disabled="data.is_saved"
								/>
								<DeskControl
									v-model="doc.company"
									options="Company"
									:label="__('Company')"
									:disabled="data.is_saved"
								/>
							</div>
							<DeskControl
								v-model="doc.warehouse"
								options="Warehouse"
								:label="__('Store')"
								:filters="warehouseFilters"
							/>
						</section>

						<section v-if="data.is_saved" class="space-y-3">
							<SectionHead
								:title="__('Machines')"
								:description="
									__('Workstations on this floor and what each one is doing now.')
								"
							/>
							<div
								v-if="machines.length"
								class="divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-2"
							>
								<div
									v-for="(machine, i) in machines"
									:key="machine.name"
									class="flex h-14 items-center gap-3 px-3"
									@mouseenter="focus = i"
									@mouseleave="focus = null"
								>
									<span
										class="size-4 shrink-0 text-ink-gray-6"
										:class="machineOf(machine.machine_model).icon"
										aria-hidden="true"
									/>
									<div class="min-w-0 flex-1">
										<button
											class="block max-w-full truncate text-left text-base font-medium text-ink-gray-8 hover:underline"
											@click="openForm('Workstation', machine.name)"
										>
											{{ machine.name }}
										</button>
										<button
											v-if="machine.job"
											class="block max-w-full truncate text-left text-sm text-ink-gray-5 hover:text-ink-gray-7"
											@click="setRoute('run', machine.job.work_order)"
										>
											{{
												__("{0} for {1}", [
													machine.job.operation,
													machine.job.work_order,
												])
											}}
										</button>
										<p v-else class="truncate text-sm text-ink-gray-5">
											{{ machine.workstation_type || __("No Workstation Type") }}
										</p>
									</div>
									<Badge
										:label="__(machine.status || 'Off')"
										:theme="statusOf(machine).theme"
										variant="subtle"
									/>
									<Tooltip v-if="!readOnly" :text="__('Remove from Floor')">
										<Button
											variant="ghost"
											size="sm"
											icon="lucide-x"
											:aria-label="__('Remove from Floor')"
											@click="setFloor(machine.name, null)"
										/>
									</Tooltip>
								</div>
							</div>
							<DeskControl
								v-if="!readOnly"
								v-model="adding"
								options="Workstation"
								:label="__('Add Machine')"
								:filters="machineFilters"
							/>
						</section>

						<section v-if="data.is_saved" class="space-y-3">
							<SectionHead
								:title="__('Work Orders')"
								:description="__('Open Work Orders that run on these machines.')"
							/>
							<div
								v-if="data.work_orders.length"
								class="divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-2"
							>
								<button
									v-for="order in data.work_orders"
									:key="order.name"
									class="flex h-14 w-full items-center gap-3 px-3 text-left hover:bg-surface-gray-1"
									@click="setRoute('run', order.name)"
								>
									<div class="min-w-0 flex-1">
										<p class="truncate text-base font-medium text-ink-gray-8">
											{{ order.name }}
										</p>
										<p class="truncate text-sm text-ink-gray-5">
											{{ order.item_name }} · {{ fmt(order.produced_qty) }} /
											{{ fmt(order.qty) }}
											{{ order.stock_uom }}
										</p>
									</div>
									<Badge :label="__(order.status)" variant="subtle" />
								</button>
							</div>
							<p v-else class="text-p-sm text-ink-gray-5">
								{{ __("No open Work Order uses these machines.") }}
							</p>
						</section>
					</fieldset>
				</ScrollArea>
			</aside>
			<div class="relative min-w-0 flex-1 bg-surface-gray-1">
				<PlantScene :plant="scenePlant" :view="view" :live="live">
					<template v-if="!machines.length" #overlay>
						<div
							class="w-80 rounded-5 border border-outline-gray-2 bg-surface-base p-4 shadow-sm"
						>
							<p class="text-base-semibold text-ink-gray-8">{{ __("No machines yet") }}</p>
							<p class="mt-1 text-p-sm text-ink-gray-6">
								{{
									data.is_saved
										? __("Add a machine on the left to place it here.")
										: __("Save the floor, then add its machines.")
								}}
							</p>
						</div>
					</template>
				</PlantScene>
			</div>
		</div>
	</div>
</template>
