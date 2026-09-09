import os
import vertexai
from vertexai import agent_engines
from dotenv import load_dotenv

from api.agent import (
    retrieve_from_script,
    generate_storyboard_tool,
    script_doctor_tool,
    parallel_search
)
from vertexai.preview.reasoning_engines import LangchainAgent

def deploy():
    load_dotenv()
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "mock-project-id")
    LOCATION = os.getenv("BQ_REGION", "us-central1")
    STAGING_BUCKET = os.getenv("GCS_BUCKET", "sceneiq-storyboards")
    
    print(f"Initializing Vertex AI for {PROJECT_ID} in {LOCATION} with bucket {STAGING_BUCKET}...")
    vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=f"gs://{STAGING_BUCKET}")
    
    print("Initializing LangchainAgent...")
    agent = LangchainAgent(
        model="gemini-2.5-flash",
        tools=[retrieve_from_script, generate_storyboard_tool, script_doctor_tool, parallel_search],
        agent_executor_kwargs={"return_intermediate_steps": True}
    )
    
    print("Deploying agent to Vertex AI Agent Engine... This will take several minutes.")
    try:
        remote_agent = agent_engines.create(
            agent,
            requirements=[
                "google-cloud-aiplatform[agent_engines,langchain]",
                "cloudpickle==3.0.0",
                "pydantic>=2.10",
                "requests",
                "google-genai",
                "langchain-google-genai"
            ]
        )
        print("\\nDeployment Successful!")
        print(f"Agent Resource Name: {remote_agent.resource_name}")
    except Exception as e:
        print(f"\\nDeployment Failed: {e}")

if __name__ == "__main__":
    deploy()
