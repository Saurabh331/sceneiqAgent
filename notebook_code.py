# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# --- CELL ---

%pip install --upgrade --quiet \
    "google-cloud-aiplatform[agent_engines,langchain]" \
    cloudpickle==3.0.0 \
    "pydantic>=2.10" \
    requests

# --- CELL ---

# Restart kernel after installs so that your environment can access the new packages
import IPython

app = IPython.Application.instance()
app.kernel.do_shutdown(True)

# --- CELL ---

import sys

if "google.colab" in sys.modules:
    from google.colab import auth

    auth.authenticate_user()

# --- CELL ---

PROJECT_ID = "[your-project-id]"  # @param {type:"string"}
LOCATION = "us-central1"  # @param {type:"string"}
STAGING_BUCKET = "gs://[your-staging-bucket]"  # @param {type:"string"}

import vertexai

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

# --- CELL ---

from vertexai import agent_engines
from vertexai.preview.reasoning_engines import LangchainAgent

# --- CELL ---

model = "gemini-3.8-flash"

# --- CELL ---

def get_exchange_rate(
    currency_from: str = "USD",
    currency_to: str = "EUR",
    currency_date: str = "latest",
):
    """Retrieves the exchange rate between two currencies on a specified date."""
    import requests

    response = requests.get(
        f"https://api.frankfurter.app/{currency_date}",
        params={"from": currency_from, "to": currency_to},
    )
    return response.json()

# --- CELL ---

get_exchange_rate(currency_from="USD", currency_to="SEK")

# --- CELL ---

agent = LangchainAgent(
    model=model,
    tools=[get_exchange_rate],
    agent_executor_kwargs={"return_intermediate_steps": True},
)

# --- CELL ---

agent.query(input="What's the exchange rate from US dollars to Swedish currency today?")

# --- CELL ---

message_types = {"actions": "Action", "messages": "Message", "output": "Output"}
for chunk in agent.stream_query(
    input="What's the exchange rate from US dollars to Swedish currency today?"
):
    for key, label in message_types.items():
        if key in chunk:
            print("\n------\n")
            print(f"{label}:")
            print()
            print(chunk[key])

# --- CELL ---

agent = LangchainAgent(
    model=model,
    tools=[get_exchange_rate],
)

# --- CELL ---

remote_agent = agent_engines.create(
    agent,
    requirements=[
        "google-cloud-aiplatform[agent_engines,langchain]",
        "cloudpickle==3.0.0",
        "pydantic>=2.10",
        "requests",
    ],
)

# --- CELL ---

remote_agent.query(
    input="What's the exchange rate from US dollars to Swedish currency today?"
)

# --- CELL ---

message_types = {"actions": "Action", "messages": "Message", "output": "Output"}
for chunk in remote_agent.stream_query(
    input="What's the exchange rate from US dollars to Swedish currency today?"
):
    for key, label in message_types.items():
        if key in chunk:
            print("\n------\n")
            print(f"{label}:")
            print()
            print(chunk[key])

# --- CELL ---

remote_agent.resource_name

# --- CELL ---

# from vertexai import agent_engines

# AGENT_ENGINE_RESOURCE_NAME = "YOUR_AGENT_ENGINE_RESOURCE_NAME"  # Replace with the resource name of your deployed Agent Engine

# remote_agent = agent_engines.get(AGENT_ENGINE_RESOURCE_NAME)
# response = remote_agent.query(input=query)

# --- CELL ---

## Model variant and version
model = "gemini-3.8-flash"

## Model safety settings
from langchain_google_vertexai import HarmBlockThreshold, HarmCategory

safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

## Model parameters
model_kwargs = {
    "temperature": 0.3,
    "max_output_tokens": 1000,
    "top_p": 0.95,
    "top_k": 40,
    "safety_settings": safety_settings,
}

# --- CELL ---

# Agent parameters
agent_executor_kwargs = {
    "return_intermediate_steps": True,
    "max_iterations": 3,
    "handle_parsing_errors": False,
    "trim_intermediate_steps": -1,
}

# --- CELL ---

remote_agent.delete()