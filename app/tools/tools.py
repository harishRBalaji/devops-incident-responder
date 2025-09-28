# app/tools/tools.py
import os
import boto3
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
    """Return a single embedding vector for the given text."""
    resp = client.embeddings.create(model=model, input=text)
    return resp.data[0].embedding


def _read_local_log(incident_id: str) -> str:
    """
    Read local log at: app/logs/<incident_id>/<incident_id>.log
    (fallback to app/logs/<incident_id>.log if someone placed it flat).
    """
    root = os.getenv("LOGS_LOCAL_ROOT", "app/logs")
    path = os.path.join(root, incident_id, f"{incident_id}.log")
    if not os.path.exists(path):
        alt = os.path.join(root, f"{incident_id}.log")
        if not os.path.exists(alt):
            raise FileNotFoundError(
                f"Local log not found at {path} (or {alt}). "
                "Expected layout: app/logs/INC003/INC003.log"
            )
        path = alt
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _read_s3_log(incident_id: str) -> str:
    """
    Read S3 log at: s3://<bucket>/<incident_id>/<incident_id>.log
    """
    bucket = os.getenv("S3_BUCKET_NAME") or os.getenv("S3_BUCKET") or ""
    if not bucket:
        raise ValueError("Set S3_BUCKET_NAME (or S3_BUCKET) in your environment.")

    region = os.getenv("S3_REGION") or os.getenv("AWS_REGION") or "us-east-1"
    # Let boto3 resolve credentials (env, ~/.aws/credentials, or IAM role)
    s3 = boto3.client("s3", region_name=region)

    key = f"{incident_id}/{incident_id}.log"

    # Fast path: try exact key
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read().decode("utf-8", errors="replace")
    except s3.exceptions.NoSuchKey:
        pass
    except Exception:
        # fall through to a clearer error below
        pass

    # Minimal diagnostic: does the folder exist?
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=f"{incident_id}/")
    contents = resp.get("Contents", [])
    if not contents:
        raise FileNotFoundError(
            f"No S3 objects under prefix '{incident_id}/' in bucket '{bucket}'. "
            f"Expected key: {key}"
        )

    raise FileNotFoundError(
        f"S3 object not found: s3://{bucket}/{key}. "
        f"Found under folder: {[c['Key'] for c in contents][:5]}"
    )


# === Tools ===
@tool
def fetch_log_file(incident_id: str, phase_title: str, synopsis: str) -> str:
    """
    Fetch the raw log file for a given incident from local disk (dev) or S3 (prod).

    Layouts:
      - Local: app/logs/<incident_id>/<incident_id>.log
      - S3:    s3://<bucket>/<incident_id>/<incident_id>.log
    """
    step_id = record_step(incident_id, phase_title, synopsis, phase="in_progress")
    try:
        mode = (os.getenv("LOGS_MODE", "local") or "local").lower()
        if mode == "local":
            log_data = _read_local_log(incident_id)
        else:
            log_data = _read_s3_log(incident_id)

        update_step_status(step_id, "complete")
        return log_data
    except Exception as e:
        update_step_status(step_id, "error")
        raise e


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
        for m in getattr(results, "matches", []) or []:
            meta = getattr(m, "metadata", {}) or {}
            docs.append(meta.get("text", ""))

        update_step_status(step_id, "complete")
        return "\n\n".join(docs)
    except Exception as e:
        update_step_status(step_id, "error")
        raise e


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
        return f"Failed to store report: {e}"
