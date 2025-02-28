<script lang="ts">
  export let variant: 'default' | 'outline' = 'default';
  export let class_name = '';
  export let class_content = '';

  const variantClasses = {
    default: 'bg-white dark:bg-gray-800 shadow-sm',
    outline: 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'
  };

  $: cardClasses = `
    ${variantClasses[variant]}
    rounded-lg
    ${class_name}
  `;
</script>

<div class={cardClasses} {...$$restProps}>
  <div class={class_content}>
    <slot />
  </div>
</div> 