import os
import boto3
import pinecone
from openai import OpenAI
from dotenv import load_dotenv
from langchain.agents import tool
from db.dal import record_step, update_step_status, save_report

load_dotenv()

# Initialize clients
client = OpenAI()
pinecone.init(
    api_key=os.getenv("PINECONE_API_KEY"),
    environment=os.getenv("PINECONE_ENV")
)

INDEX_NAME = "incident-rag"

# === Tools ===

@tool
def fetch_log_file(incident_id: str, phase_title: str, synopsis: str) -> str:
    """
    Fetch the log file for the given incident_id from S3.

    Input arguments required:
      - incident_id: the unique identifier of the incident being investigated
      - phase_title: a short title describing this step to be rendered in the UI
      - synopsis: a 1-2 sentence description of what is being attempted

    Behavior:
      - Logs the step into the agent_steps table using store_step()
      - Fetches the first log file from the S3 bucket under prefix <incident_id>/
        where logs are stored in the format:
          s3://<S3_BUCKET_NAME>/<incident_id>/<incident_id>_xxx.log
      - Returns the raw log file content as a string
    """
    step_id = record_step(incident_id, phase_title, synopsis, phase="in_progress")
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-2")
        )
        bucket_name = os.getenv("S3_BUCKET_NAME")
        prefix = f"{incident_id}/"

        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if "Contents" not in response:
            raise FileNotFoundError(f"No log files found in S3 for incident_id={incident_id}")

        log_key = response["Contents"][0]["Key"]
        obj = s3.get_object(Bucket=bucket_name, Key=log_key)
        log_data = obj["Body"].read().decode("utf-8")

        update_step_status(step_id, "complete")
        return log_data
    except Exception as e:
        update_step_status(step_id, "error")
        raise

def get_embedding(text: str, model="text-embedding-3-small"):
    """Generate embeddings for the given text."""
    resp = client.embeddings.create(model=model, input=text)
    return resp.data[0].embedding


@tool
def rag_retrieve(incident_id: str, log_data: str, phase_title: str, synopsis: str) -> str:
    """
    Retrieve top relevant Knowledge Base documents from Pinecone given a log file string.

    Input arguments required:
      - incident_id: the unique identifier of the incident being investigated
      - log_data: the raw log file text to base the retrieval on
      - phase_title: a short title describing this step to be rendered in the UI
      - synopsis: a 1-2 sentence description of what is being attempted

    Behavior:
      - Logs the step into the agent_steps table using store_step()
      - Retrieves the top 3 most relevant Knowledge Base documents from Pinecone
      - Returns the concatenated text of these documents for further analysis
    """
    step_id = record_step(incident_id, phase_title, synopsis, phase="in_progress")
    try:
        index = pinecone.Index(INDEX_NAME)
        embedding = get_embedding(log_data)
        results = index.query(vector=embedding, top_k=3, include_metadata=True)
        docs = [match["metadata"].get("text", "") for match in results["matches"]]
        update_step_status(step_id, "complete")
        return "\n\n".join(docs)
    except Exception:
        update_step_status(step_id, "error")
        raise

@tool
def store_final_report(incident_id: str, phase_title: str, synopsis: str, incident_report_text: str) -> str:
    """
    Store the final RCA report in the DB.

    Input arguments required:
      - incident_id: the unique identifier of the incident being investigated
      - phase_title: a short title describing this step to be rendered in the UI
      - synopsis: a 1-2 sentence description of what is being attempted
      - incident_report_text: the full comprehensive incident report text
        (not JSON, but a narrative document containing incident summary, timeline,
        log evidence, root cause, business impact, and mitigation steps)

    Behavior:
      - Logs the action into the agent_steps table using store_step()
      - Saves the incident_report_text in the reports table for the given incident_id
      - Returns a success or error message
    """
    step_id = record_step(incident_id, phase_title, synopsis, phase="in_progress")
    try:
        save_report(incident_id, incident_report_text)
        update_step_status(step_id, "complete")
        return "Report stored successfully."
    except Exception as e:
        update_step_status(step_id, "error")
        return f"Failed to store report: {e}"