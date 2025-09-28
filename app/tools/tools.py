# app/tools/tools.py
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
from openai import OpenAI
from dotenv import load_dotenv
from langchain.agents import tool
from pinecone import Pinecone
from app.db.dal import record_step, update_step_status, save_report

load_dotenv()

# ---- Clients ----
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# ---- Helpers ----
def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    resp = client.embeddings.create(model=model, input=text)
    return resp.data[0].embedding

def _emit_error_step(incident_id: str, title: str, exc: Exception, context: dict) -> None:
    """
    Write a second step with details so the UI shows why it failed.
    Avoid printing secrets; include only non-sensitive context.
    """
    safe = "\n".join([f"{k}={v}" for k, v in context.items() if v is not None])
    msg = f"{type(exc).__name__}: {exc}\n\nContext:\n{safe}"
    # Create an error step row; marked 'error' so it renders red.
    record_step(incident_id, title, msg, phase="error")

def _read_local_log(incident_id: str) -> str:
    """
    Read local log at: app/logs/<incident_id>/<incident_id>.log
    (fallback: app/logs/<incident_id>.log)
    """
    root = os.getenv("LOGS_LOCAL_ROOT", "app/logs")
    expected = os.path.join(root, incident_id, f"{incident_id}.log")
    alt = os.path.join(root, f"{incident_id}.log")

    if os.path.exists(expected):
        path = expected
    elif os.path.exists(alt):
        path = alt
    else:
        raise FileNotFoundError(
            f"Local log not found. Tried: {expected} and {alt}"
        )

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def _read_s3_log(incident_id: str) -> str:
    raw_bucket = os.getenv("S3_BUCKET_NAME") or os.getenv("S3_BUCKET") or ""
    # normalize: strip scheme and trailing slashes
    bucket = raw_bucket.replace("s3://", "").strip().strip("/")
    if not bucket:
        raise ValueError("S3 bucket not set. Define S3_BUCKET_NAME (or S3_BUCKET).")

    region = os.getenv("S3_REGION") or os.getenv("AWS_REGION") or "us-east-1"
    key = f"{incident_id}/{incident_id}.log"
    s3 = boto3.client("s3", region_name=region)

    s3.head_object(Bucket=bucket, Key=key)           # will raise with clear error if wrong
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read().decode("utf-8", errors="replace")


# === Tools ===
@tool
def fetch_log_file(incident_id: str, phase_title: str, synopsis: str) -> str:
    """
    Fetch the raw log file for a given incident from local disk (dev) or S3 (prod).

    Layouts:
      - Local: app/logs/<incident_id>/<incident_id>.log   (fallback: app/logs/<incident_id>.log)
      - S3:    s3://<bucket>/<incident_id>/<incident_id>.log
    """
    step_id = record_step(incident_id, phase_title, synopsis, phase="in_progress")
    mode = (os.getenv("LOGS_MODE", "local") or "local").lower()
    try:
        if mode == "local":
            log_data = _read_local_log(incident_id)
        else:
            bucket = os.getenv("S3_BUCKET_NAME") or os.getenv("S3_BUCKET")
            region = os.getenv("S3_REGION") or os.getenv("AWS_REGION")
            key = f"{incident_id}/{incident_id}.log"
            log_data = _read_s3_log(incident_id)  # raises with detailed message

        update_step_status(step_id, "complete")
        return log_data

    except Exception as e:
        update_step_status(step_id, "error")
        # Add a separate error step with details so UI shows the cause.
        context = {
            "mode": mode,
            "bucket": os.getenv("S3_BUCKET_NAME") or os.getenv("S3_BUCKET"),
            "region": os.getenv("S3_REGION") or os.getenv("AWS_REGION"),
            "key": f"{incident_id}/{incident_id}.log",
            "logs_local_root": os.getenv("LOGS_LOCAL_ROOT", "app/logs"),
        }
        _emit_error_step(incident_id, "Fetch logs failed", e, context)
        # Re-raise so the agent flow stops (as before).
        raise

@tool
def rag_retrieve(incident_id: str, log_data: str, phase_title: str, synopsis: str) -> str:
    """
    Retrieve top relevant Knowledge Base documents from Pinecone for the given log text.
    """
    step_id = record_step(incident_id, phase_title, synopsis, phase="in_progress")
    try:
        index = pc.Index(INDEX_NAME)
        embedding = get_embedding(log_data)
        results = index.query(vector=embedding, top_k=3, include_metadata=True)

        docs = []
        # pinecone-py returns an object with .matches; make it safe
        matches = getattr(results, "matches", None) or getattr(results, "get", lambda k, d=None: d)("matches", []) or []
        for m in matches:
            meta = getattr(m, "metadata", None) or m.get("metadata", {}) if isinstance(m, dict) else {}
            docs.append(meta.get("text", ""))

        update_step_status(step_id, "complete")
        return "\n\n".join(docs)
    except Exception as e:
        update_step_status(step_id, "error")
        _emit_error_step(incident_id, "RAG retrieval failed", e, {"index": INDEX_NAME})
        raise

@tool
def store_final_report(incident_id: str, phase_title: str, synopsis: str, incident_report_text: str) -> str:
    """
    Persist the final HTML incident report in the DB.
    """
    step_id = record_step(incident_id, phase_title, synopsis, phase="in_progress")
    try:
        save_report(incident_id, incident_report_text)
        update_step_status(step_id, "complete")
        return "Report stored successfully."
    except Exception as e:
        update_step_status(step_id, "error")
        _emit_error_step(incident_id, "Store report failed", e, {})
        return f"Failed to store report: {e}"
