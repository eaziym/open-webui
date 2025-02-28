<script>
  import { createEventDispatcher } from 'svelte';
  import { notionIntegration } from '$lib/stores/integrations';
  
  export let message;
  export let onSubmit;
  
  const dispatch = createEventDispatcher();
  
  function handleListDatabases() {
    // Format a message to list databases
    const prompt = "List all my Notion databases";
    dispatch('message', { text: prompt });
    if (onSubmit) onSubmit(prompt);
  }
  
  function handleQueryDatabase() {
    // Format a message to query a database
    const prompt = "Show me the tasks in my Tasks database";
    dispatch('message', { text: prompt });
    if (onSubmit) onSubmit(prompt);
  }
  
  function handleCreatePage() {
    // Format a message to create a new page
    const prompt = "Create a new task in my Tasks database with title 'Test Task' and status 'To Do'";
    dispatch('message', { text: prompt });
    if (onSubmit) onSubmit(prompt);
  }
  
  function handleCustomQuery() {
    // Use the custom message from the input
    if (message && message.trim().length > 0) {
      dispatch('message', { text: message });
      if (onSubmit) onSubmit(message);
    }
  }
</script>

<div class="w-full p-4 bg-input-background rounded-md">
  <h3 class="text-lg font-medium mb-2">Notion Integration</h3>
  
  {#if $notionIntegration && $notionIntegration.active}
    <div class="mb-4">
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Connected to Notion workspace: <span class="font-medium">{$notionIntegration.workspace_name}</span>
      </p>
    </div>
    
    <div class="flex flex-col gap-2 mb-4">
      <button
        class="btn btn-primary py-2 px-4"
        on:click={handleListDatabases}
      >
        List My Databases
      </button>
      
      <button
        class="btn btn-primary py-2 px-4"
        on:click={handleQueryDatabase}
      >
        Query Tasks Database
      </button>
      
      <button
        class="btn btn-primary py-2 px-4"
        on:click={handleCreatePage}
      >
        Create a New Task
      </button>
    </div>
    
    <div class="mt-4">
      <p class="text-sm mb-2">Or type a custom Notion request:</p>
      <div class="flex gap-2">
        <input
          bind:value={message}
          class="input-bordered input flex-1"
          placeholder="E.g., Show me all pages in my Knowledge Base"
        />
        <button
          class="btn btn-primary py-2 px-4"
          on:click={handleCustomQuery}
        >
          Send
        </button>
      </div>
    </div>
  {:else}
    <div class="text-error">
      <p>Notion integration not connected.</p>
      <p class="mt-2">
        Please connect your Notion account in the settings.
      </p>
    </div>
  {/if}
</div> 