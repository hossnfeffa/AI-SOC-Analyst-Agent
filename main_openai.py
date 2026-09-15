# API Keys: https://platform.openai.com/settings/organization/api-keys
# Billing:  https://platform.openai.com/settings/organization/billing/overview

from openai import OpenAI

openai_client = OpenAI(api_key="____ your OpenAI API key goes here ____")

prompt = "Give me a very short recipe for a cake please."

response = openai_client.chat.completions.create(
    model="gpt-5",
    messages=[{"role": "user", "content": prompt}]
)

answer = response.choices[0].message.content

print(f"\n{answer}\n")