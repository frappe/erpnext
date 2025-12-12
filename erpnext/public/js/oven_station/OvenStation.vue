<script setup>
import { ref } from 'vue';

const incomingSlabs = ref([
  { serial: 'SLB-2024-8841', subtitle: 'Ready 17:43' },
  { serial: 'SLB-2024-8842', subtitle: 'Ready 17:46' },
]);

const racks = ref([
  { slot: 'A-1', state: 'curing', serial: 'SLB-2024-8839', colour: 'Midnight Blue', time_text: '15m Left' },
  { slot: 'A-2', state: 'curing', serial: 'SLB-2024-8840', colour: 'Carrara White', time_text: '35m Left' },
  { slot: 'A-3', state: 'empty' },
  { slot: 'A-4', state: 'empty' },
  { slot: 'B-1', state: 'overheat', serial: 'SLB-2024-8838', colour: 'Concrete Grey', time_text: '10m OVER' },
  { slot: 'B-2', state: 'maintenance' },
  { slot: 'B-3', state: 'empty' },
  { slot: 'B-4', state: 'empty' },
]);

const selectedSlab = ref(null);

function selectSlab(slab) {
  selectedSlab.value = slab.serial;
}

function loadIntoRack(rack) {
  if (rack.state !== 'empty') return;
  if (!selectedSlab.value) {
    frappe.msgprint(__('Please select an incoming slab first.'));
    return;
  }

  frappe.confirm(
    __('Load slab {0} into rack {1}?', [selectedSlab.value, rack.slot]),
    () => {
      // YES: update rack to curing
      rack.state = 'curing';
      rack.serial = selectedSlab.value;
      rack.colour = 'Carrara White'; // later from real data
      rack.time_text = '45m Left';

      // remove slab from incoming list
      const idx = incomingSlabs.value.findIndex(s => s.serial === selectedSlab.value);
      if (idx !== -1) incomingSlabs.value.splice(idx, 1);
      selectedSlab.value = null;
    }
  );
}

function rackClasses(rack) {
  if (rack.state === 'curing') return 'rack-card curing';
  if (rack.state === 'overheat') return 'rack-card overheat';
  if (rack.state === 'maintenance') return 'rack-card maintenance';
  return 'rack-card empty';
}
</script>

<template>
  <div class="page-card d-flex">
    <!-- Left: Incoming Slabs -->
    <div style="width:540px;" class="pr-4 border-right">
      <h5 class="mb-3 d-flex align-items-center">
        <span class="mr-2">+</span> {{ __('Incoming Slabs') }}
      </h5>
      <div class="text-muted small mb-3">
        {{ __('Select a slab to load into an empty rack.') }}
      </div>

      <div class="incoming-list">
        <div v-for="slab in incomingSlabs" :key="slab.serial"
             class="incoming-item mb-2 p-3 d-flex align-items-center border rounded"
             :style="{ background: selectedSlab === slab.serial ? '#e2edff' : '#f8f9fa', cursor: 'pointer' }"
             @click="selectSlab(slab)">
          <div style="width:32px;height:32px;border-radius:4px;background:#1f2937;" class="mr-3"></div>
          <div class="flex-fill">
            <div class="font-weight-bold small">{{ slab.serial }}</div>
            <div class="text-muted small">
              <span class="fa fa-clock-o mr-1"></span>{{ slab.subtitle }}
            </div>
          </div>
          <div class="text-muted">
            <span class="fa fa-arrow-right"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Center: Oven Monitor -->
    <div class="flex-fill pl-4">
      <div class="d-flex justify-content-between">
        <div>
          <h4 class="mb-1">{{ __('Oven Monitor (Line A)') }}</h4>
          <div class="text-muted small mb-4">
            {{ __('Manage curing process and rack assignments.') }}
          </div>
        </div>

        <div class="d-flex mb-3 justify-content-end align-items-center">
          <span class="small mr-3 d-flex align-items-center">
            <span class="mr-1 border rounded d-flex" style="background:#b1b8bf; width:1rem; height:1rem;"></span>{{ __('Empty') }}
          </span>
          <span class="small mr-3 d-flex align-items-center">
            <span class="mr-1 border rounded d-flex" style="background:#3bc63b; width:1rem; height:1rem;"></span>{{ __('Curing') }}
          </span>
          <span class="small mr-3 d-flex align-items-center">
            <span class="mr-1 border rounded d-flex" style="background:#ef2e3f; width:1rem; height:1rem;"></span>{{ __('Overheating') }}
          </span>
          <span class="small d-flex align-items-center">
            <span class="mr-1 border rounded d-flex" style="background:#78afe6; width:1rem; height:1rem;"></span>{{ __('Maintenance') }}
          </span>
        </div>
      </div>

      <div class="rack-grid d-flex flex-wrap">
        <div v-for="rack in racks" :key="rack.slot"
             :class="rackClasses(rack)"
             class="mb-3 mr-3 p-3 rounded"
             style="width:225px;height:210px;display:flex;flex-direction:column;"
             @click="loadIntoRack(rack)">
          <div class="text-muted small mb-1">{{ rack.slot }}</div>
          <div class="d-flex align-items-center justify-content-center flex-fill">
            <!-- empty -->
            <div v-if="rack.state === 'empty'" class="text-center text-muted">
              <div class="mb-3"><span class="fa fa-inbox" style="font-size:1.5rem;"></span></div>
              <div class="font-weight-bold">{{ __('LOAD HERE') }}</div>
            </div>
            <!-- curing -->
            <div v-else-if="rack.state === 'curing'" class="text-center">
              <div class="font-weight-bold mb-1">{{ rack.serial }}</div>
              <div class="text-muted small mb-1">{{ rack.colour }}</div>
              <div class="text-muted small">
                <span class="fa fa-clock-o mr-1"></span>{{ rack.time_text }}
              </div>
            </div>
            <!-- overheat -->
            <div v-else-if="rack.state === 'overheat'" class="text-center">
              <div class="font-weight-bold mb-1">{{ rack.serial }}</div>
              <div class="text-muted small mb-1">{{ rack.colour }}</div>
              <div class="text-danger small">
                <span class="fa fa-thermometer-full mr-1"></span>{{ rack.time_text }}
              </div>
            </div>
            <!-- maintenance -->
            <div v-else-if="rack.state === 'maintenance'" class="text-center text-muted">
              <div class="mb-2">
                <span class="fa fa-exclamation-triangle mr-1" style="font-size:1.4rem;"></span>
              </div>
              <div class="font-weight-bold">{{ __('MAINTENANCE') }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.rack-card {
  border: 2px dashed #ced4da;
  background: #f8f9fa;
}

.rack-card.empty {
  border-style: dashed;
  border-color: #ced4da;
  background: #f8f9fa;
}

.rack-card.curing {
  border-style: solid;
  border-color: #28a745;
  background: #d4f8d4;
}

.rack-card.overheat {
  border-style: solid;
  border-color: #dc3545;
  background: #f8d7da;
}

.rack-card.maintenance {
  border-style: dashed;
  border-color: #6c757d;
  background: #e2edff;
}
</style>
