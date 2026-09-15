# API Keys: https://platform.openai.com/settings/organization/api-keys
# Billing:  https://platform.openai.com/settings/organization/billing/overview
from openai import OpenAI
from colorama import init, Fore, Style
import tiktoken
import json
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient
from datetime import timedelta
import pandas as pd

init(autoreset=True)

LOG_ANALYTICS_WORKSPACE_ID = "60c7f53e-249a-4077-b68e-55a4ae877d7c"

# Models: https://platform.openai.com/docs/models/compare
MODELS = {
    "gpt-5":        {"max_window_tokens": 400_000,   "max_output_tokens": 128_000, "cost_per_million_input": 1.25, "cost_per_million_output": 10.00},
    "gpt-4.1":      {"max_window_tokens": 1_047_576, "max_output_tokens": 32_768,  "cost_per_million_input": 1.00, "cost_per_million_output": 8.00},
    "gpt-5-mini":   {"max_window_tokens": 400_000,   "max_output_tokens": 128_000, "cost_per_million_input": 0.25, "cost_per_million_output": 2.00},
    "gpt-4.1-nano": {"max_window_tokens": 1_000_000, "max_output_tokens": 32_768,  "cost_per_million_input": 0.10, "cost_per_million_output": 0.40}
}

def query_log_analytics(client, workspace_id, query, hours_ago):

    response = client.query_workspace(
        workspace_id=workspace_id,
        query=query,
        timespan=timedelta(hours=hours_ago)
    )

    # Extract the table
    table = response.tables[0]

    if len(response.tables[0].rows) == 0:
        print("No data returned from Log Analytics.")
        exit



    # TODO: Handle if returns 0 events
    record_count = len(response.tables[0].rows)

    # Extract columns and rows using dot notation
    columns = table.columns  # Already a list of strings
    rows = table.rows        # List of row data

    df = pd.DataFrame(rows, columns=columns)
    plain_text_records = df.to_csv(index=False)

    return plain_text_records

def calculate_chat_cost(prompt_tokens, cost_per_million) -> float:
    cost = (prompt_tokens / 1_000_000) * cost_per_million
    return round(cost, 6)

def count_message_tokens(messages, model: str) -> int:
    """
    Count tokens for chat messages using the actual serialization format
    the API will send to the model.
    """
    # serialize the messages the same way OpenAI client does
    payload = {"model": model, "messages": messages}
    serialized = json.dumps(payload, ensure_ascii=False)

    # handle unsupported models manually
    if model == "gpt-5":
        enc = tiktoken.get_encoding("cl100k_base")
    else:
        # choose encoding that matches the model family
        enc = tiktoken.encoding_for_model(model)

    return len(enc.encode(serialized))

openai_client = OpenAI(api_key="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")

# Need Azure CLI: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows?view=azure-cli-latest&pivots=msi
log_analytics_client = LogsQueryClient(credential=DefaultAzureCredential())

# ----------------------------------------------------------------------------
# Models: https://platform.openai.com/docs/models/compare

# more window -> more completion tokens -> more cost
MAX_OUTPUT_TOKENS = 5_000 

# gpt-5, gpt-4.1, gpt-5-mini, gpt-4.1-nano (in order of cost)
current_model = "gpt-5-mini" 

# more time -> more logs -> more tokens -> more cost
hours_ago = 3

# more fields -> larger logs -> more cost
kql_query = f'''   
DeviceLogonEvents
'''
# ----------------------------------------------------------------------------

logs = query_log_analytics(
    client = log_analytics_client,
    workspace_id = LOG_ANALYTICS_WORKSPACE_ID,
    query = kql_query,
    hours_ago = hours_ago
    )

prompt_messages = [
    {"role": "system", "content": "You are a threat hunter. If the user provides logs, analyze them for malicious activity."},
    {"role": "user", "content": f"Here are some logs {logs}"}
    ]

estimated_prompt_token_count = count_message_tokens(messages=prompt_messages, model=current_model)

# We can restrict max output tokens
max_tokens_used_in_response = MAX_OUTPUT_TOKENS
# max_tokens_used_in_response = models[current_model]["max_output_tokens"]

# Loop through each model and show the estimated cost
for model, details in MODELS.items():
    model_cost_per_million_tokens_input = MODELS[model]["cost_per_million_input"]
    model_cost_per_million_tokens_output = MODELS[model]["cost_per_million_output"]

    estimated_chat_cost_input = calculate_chat_cost(
        prompt_tokens=estimated_prompt_token_count,
        cost_per_million=model_cost_per_million_tokens_input
    )

    estimated_chat_cost_output = calculate_chat_cost(
        prompt_tokens=max_tokens_used_in_response,
        cost_per_million=model_cost_per_million_tokens_output
    )

    estimated_total_chat_cost = estimated_chat_cost_input + estimated_chat_cost_output

    print(f"\nModel: {model}")
    print(f"Estimated input tokens:  {estimated_prompt_token_count}")
    print(f"Estimated output tokens: {max_tokens_used_in_response}")
    print(f"Estimated chat cost:     ${estimated_total_chat_cost:.4f}")

exit(0)

input(f"\nPress any key to proceed with model {current_model}...")

# Rate Limit Explanation: https://platform.openai.com/docs/guides/rate-limits
# Rate Limits by Model:   https://platform.openai.com/docs/models/compare
response = openai_client.chat.completions.create(
    model=current_model,
    messages=prompt_messages,
    max_completion_tokens=max_tokens_used_in_response
)

actual_tokens_input = response.usage.prompt_tokens
actual_tokens_output = response.usage.completion_tokens
actual_total_tokens = response.usage.total_tokens

actual_chat_cost_input = calculate_chat_cost(
    prompt_tokens=actual_tokens_input,
    cost_per_million=model_cost_per_million_tokens_input
)

actual_chat_cost_output = calculate_chat_cost(
    prompt_tokens=actual_tokens_output,
    cost_per_million=model_cost_per_million_tokens_output
)

actual_total_chat_cost = actual_chat_cost_input + actual_chat_cost_output

status_cost = (Fore.GREEN + "UNDER" + Style.RESET_ALL) if actual_total_chat_cost <= estimated_total_chat_cost else (Fore.RED + "OVER" + Style.RESET_ALL)
status_tokens_input = (Fore.GREEN + "UNDER" + Style.RESET_ALL) if actual_tokens_input <= estimated_prompt_token_count else (Fore.RED + "OVER" + Style.RESET_ALL)
status_tokens_output = (Fore.GREEN + "UNDER" + Style.RESET_ALL) if actual_tokens_output <= max_tokens_used_in_response else (Fore.RED + "OVER" + Style.RESET_ALL)


print()
print(f"Actual input tokens:     {actual_tokens_input} [{status_tokens_input}]")
print(f"Actual output tokens:    {actual_tokens_output} [{status_tokens_output}]")
print(f"Actual chat cost:        ${actual_total_chat_cost:.4f} [{status_cost}]")

answer = response.choices[0].message.content

# Remove the comment on print if you want to see the actual threat hunt results
# print(answer)

print("\nfin.")
