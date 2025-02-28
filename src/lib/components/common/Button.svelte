<script lang="ts">
  export let color: 'blue' | 'red' | 'green' | 'gray' | 'default' = 'default';
  export let size: 'xs' | 'sm' | 'md' | 'lg' | 'xl' = 'md';
  export let loading = false;
  export let disabled = false;
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let className = '';

  const sizeClasses = {
    xs: 'px-2 py-1 text-xs',
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-5 py-2.5 text-lg',
    xl: 'px-6 py-3 text-xl'
  };

  const colorClasses = {
    default: 'bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-white',
    blue: 'bg-blue-500 hover:bg-blue-600 text-white',
    red: 'bg-red-500 hover:bg-red-600 text-white',
    green: 'bg-green-500 hover:bg-green-600 text-white',
    gray: 'bg-gray-500 hover:bg-gray-600 text-white'
  };

  $: buttonClasses = `
    ${sizeClasses[size]}
    ${colorClasses[color]}
    rounded-md font-medium transition-colors
    focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
    ${disabled || loading ? 'opacity-50 cursor-not-allowed' : ''}
    ${className}
  `;
</script>

<button
  {type}
  class={buttonClasses}
  disabled={disabled || loading}
  on:click
  {...$$restProps}
>
  {#if loading}
    <span class="inline-block animate-spin mr-2">
      <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </span>
  {/if}
  <slot />
</button> 