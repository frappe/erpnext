<script setup>
import { onMounted, ref } from "vue";
import { Button } from "frappe-ui";
import { __, call, setRoute } from "../lib/api";
import { machineOf } from "../lib/machines";
import { fmt, plural } from "../lib/format";

const emit = defineEmits(["title", "actions"]);
const plants = ref([]);
const loading = ref(true);

onMounted(async () => {
	emit("title", __("Plant Builder"));
	emit("actions", []);
	plants.value = await call("get_plants");
	loading.value = false;
});

const open = (plant) => setRoute(plant.name);
const addPlant = () => setRoute("new");

function meta(plant) {
	const unit = plural(plant.item?.stock_uom).toLowerCase();
	const parts = [__("{0} stages", [plant.stages.length]), __("{0} raw materials", [plant.material_count])];
	if (plant.batch_size) parts.push(__("batch of {0} {1}", [fmt(plant.batch_size), unit]));
	return parts.join(" · ");
}
</script>

<template>
	<div class="min-h-0 flex-1 overflow-auto">
		<div class="mx-auto max-w-5xl px-5 pb-10 pt-6">
			<div class="flex items-start gap-4">
				<p class="max-w-[680px] flex-1 text-p-base text-ink-gray-7">
					{{
						__(
							"A plant is a formula plus a chain of machines. Set one up and the 3D plant is built from it. Then run a Work Order through it, stage by stage."
						)
					}}
				</p>
				<Button variant="solid" icon-left="lucide-plus" :label="__('New Plant')" @click="addPlant" />
			</div>
			<div class="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
				<div
					v-for="plant in plants"
					:key="plant.name"
					role="link"
					tabindex="0"
					class="flex cursor-pointer flex-col gap-3 rounded-5 border border-outline-gray-2 bg-surface-base p-4 hover:bg-surface-gray-1"
					@click="open(plant)"
					@keydown.enter="open(plant)"
				>
					<div class="flex h-8 items-center gap-1.5">
						<template v-for="(stage, i) in plant.stages" :key="i">
							<span
								v-if="i"
								class="lucide-chevron-right size-3 text-ink-gray-4"
								aria-hidden="true"
							/>
							<span
								class="flex size-8 items-center justify-center rounded-4 bg-surface-gray-2 text-ink-gray-6"
								:title="stage.stage_name"
							>
								<span
									class="size-4"
									:class="machineOf(stage.machine_model).icon"
									aria-hidden="true"
								/>
							</span>
						</template>
						<span v-if="!plant.stages.length" class="text-sm text-ink-gray-5">{{
							__("No stages yet")
						}}</span>
					</div>
					<div class="min-w-0">
						<p class="truncate text-lg-semibold text-ink-gray-8">
							{{ plant.floor_name || plant.name }}
						</p>
						<p class="truncate text-sm text-ink-gray-6">
							{{ plant.item?.item_name || __("Finished good not set yet") }}
						</p>
						<p class="mt-1 truncate text-xs text-ink-gray-5">{{ meta(plant) }}</p>
					</div>
				</div>
				<div
					role="button"
					tabindex="0"
					class="flex min-h-[11rem] cursor-pointer flex-col items-center justify-center gap-2 rounded-5 border border-dashed border-outline-gray-3 text-center hover:bg-surface-gray-1"
					@click="addPlant"
					@keydown.enter="addPlant"
				>
					<span class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
						<span class="lucide-factory block size-5" aria-hidden="true" />
					</span>
					<p class="text-base text-ink-gray-7">{{ __("Build your own plant") }}</p>
					<p class="text-sm text-ink-gray-5">{{ __("Start from a mixer and a filling line") }}</p>
				</div>
			</div>
			<p v-if="loading" class="mt-6 text-sm text-ink-gray-5">{{ __("Loading...") }}</p>
		</div>
	</div>
</template>
