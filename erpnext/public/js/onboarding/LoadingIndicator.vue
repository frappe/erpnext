<template>
  <svg
    class="loading-indicator"
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
  >
    <circle
      style="opacity: .25"
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      stroke-width="4"
    ></circle>
    <path
      style="opacity: .75"
      fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    ></path></svg
  > 
</template>
<style scoped>
.loading-indicator {
    display: inline-block;
    height: 1.25rem;
    width: 1.25rem;
    color: currentColor;
    animation: spin 1s infinite linear;
}
@keyframes spin {
    to {
        transform: rotate(1turn)
    }
}
</style>