<script setup>
import { computed, onMounted, ref } from "vue";
import { Button, Dropdown, ScrollArea, Switch } from "frappe-ui";
import MachinePreview from "../components/designer/MachinePreview.vue";
import ShapeCard from "../components/designer/ShapeCard.vue";
import { __, call, openForm } from "../lib/api";
import { PRESETS, SHAPES, isPackingModel, machineOf, newShape } from "../lib/machines";

const props = defineProps({ name: String });
const emit = defineEmits(["title", "actions"]);

const design = ref(null);
const shapes = ref([]);
const saved = ref("");
const selected = ref(null);
const running = ref(true);
const saving = ref(false);

const dirty = computed(() => JSON.stringify(shapes.value) !== saved.value);
const isPacking = computed(() => isPackingModel(design.value.machine_model));
const editable = computed(() => design.value.can_write && !isPacking.value);
const preset = computed(() => __(design.value.machine_model || machineOf("").label));

const note = computed(() => {
	if (isPacking.value) return __("Packing lines keep their own drawing.");
	if (!shapes.value.length) return __("No shapes. The plant draws the {0} preset.", [preset.value]);
	if (!design.value.is_custom && !dirty.value)
		return __("Drawn from the {0} preset. Change it and save to make your own.", [preset.value]);
	return "";
});

const withDefaults = (row) => ({ ...newShape(row.shape), ...row });
const copy = (rows) => rows.map(withDefaults);

function apply(result) {
	design.value = result;
	shapes.value = copy(result.shapes);
	saved.value = JSON.stringify(shapes.value);
	selected.value = shapes.value.length ? 0 : null;
}

onMounted(async () => {
	emit("title", props.name);
	emit("actions", [
		{ label: __("Open Workstation Type"), onClick: () => openForm("Workstation Type", props.name) },
	]);
	apply(await call("get_machine_design", { workstation_type: props.name }));
});

function insert(at, row) {
	shapes.value.splice(at, 0, row);
	selected.value = at;
}

function remove(at) {
	shapes.value.splice(at, 1);
	selected.value = shapes.value.length ? Math.min(at, shapes.value.length - 1) : null;
}

const presetOptions = Object.keys(PRESETS).map((model) => ({
	label: __(model),
	icon: machineOf(model).icon,
	onClick: () => {
		shapes.value = copy(PRESETS[model]);
		selected.value = 0;
	},
}));
const addOptions = Object.keys(SHAPES).map((shape) => ({
	label: __(shape),
	onClick: () => insert(shapes.value.length, newShape(shape)),
}));

async function save() {
	saving.value = true;
	try {
		apply(await call("save_machine_design", { workstation_type: props.name, shapes: shapes.value }));
	} finally {
		saving.value = false;
	}
}
</script>

<template>
	<div v-if="design" class="flex min-h-0 flex-1 flex-col">
		<div class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-2 px-5">
			<p class="min-w-0 flex-1 truncate text-p-sm text-ink-gray-6">{{ note }}</p>
			<template v-if="editable">
				<Dropdown :options="presetOptions">
					<Button icon-left="lucide-copy" :label="__('Copy Preset')" />
				</Dropdown>
				<Button
					:variant="dirty ? 'solid' : 'subtle'"
					icon-left="lucide-save"
					:label="__('Save')"
					:loading="saving"
					:disabled="!dirty"
					@click="save"
				/>
			</template>
		</div>
		<div class="flex min-h-0 flex-1">
			<aside class="flex w-[34rem] shrink-0 flex-col border-r border-outline-gray-2">
				<ScrollArea class="min-h-0 flex-1" viewport-class="px-5 pt-5 pb-16">
					<div class="space-y-3">
						<ShapeCard
							v-for="(shape, i) in shapes"
							:key="i"
							:shape="shape"
							:index="i"
							:selected="selected === i"
							:disabled="!editable"
							@select="selected = i"
							@duplicate="insert(i + 1, { ...shape })"
							@remove="remove(i)"
						/>
						<Dropdown v-if="editable" :options="addOptions">
							<Button icon-left="lucide-plus" :label="__('Add Shape')" />
						</Dropdown>
					</div>
				</ScrollArea>
			</aside>
			<div class="relative min-w-0 flex-1 bg-surface-gray-1">
				<MachinePreview
					:machine-model="design.machine_model"
					:shapes="shapes"
					:selected="selected"
					:running="running"
				>
					<template #overlay>
						<div
							class="w-72 rounded-5 border border-outline-gray-2 bg-surface-base p-4 shadow-sm"
						>
							<p class="text-base-semibold text-ink-gray-8">{{ __("Machine Preview") }}</p>
							<p class="mt-1 text-p-sm text-ink-gray-6">
								{{
									__(
										"Positions are measured from the machine centre, where the two grey lines cross. One grid square is 20."
									)
								}}
							</p>
							<div class="mt-3">
								<Switch v-model="running" :label="__('Run Machine')" />
							</div>
						</div>
					</template>
				</MachinePreview>
			</div>
		</div>
	</div>
</template>
