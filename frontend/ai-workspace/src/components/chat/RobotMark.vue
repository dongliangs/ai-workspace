<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <rect
      x="6"
      y="4"
      width="12"
      height="14"
      rx="4"
      fill="white"
      fill-opacity="0.95"
    />
    <circle
      cx="10"
      cy="10"
      r="1.5"
      fill="var(--aws-primary)"
    />
    <circle
      cx="14"
      cy="10"
      r="1.5"
      fill="var(--aws-primary)"
    />
    <path
      d="M9.5 14.5C10.5 15.5 13.5 15.5 14.5 14.5"
      stroke="var(--aws-primary)"
      stroke-width="1.5"
      stroke-linecap="round"
    />
    <path
      d="M12 18V21"
      stroke="white"
      stroke-width="2"
      stroke-linecap="round"
    />
    <path
      d="M8 21H16"
      stroke="white"
      stroke-width="2"
      stroke-linecap="round"
    />
  </svg>
</template>

<script setup lang="ts">
// 多词组件名：满足 vue/multi-word-component-names，且便于 devtools 识别
defineOptions({ name: 'RobotMark' })

withDefaults(defineProps<{ size?: number }>(), { size: 32 })
</script>