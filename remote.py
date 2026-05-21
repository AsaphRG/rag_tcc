import os
import sys

import vertexai
from absl import app, flags
from dotenv import load_dotenv
from vertexai import agent_engines
from vertexai.preview import reasoning_engines
from vertexai.preview.reasoning_engines import AdkApp

from admin_agent.agent import root_agent

FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket.")
flags.DEFINE_string("resource_id", None, "ReasoningEngine resource ID.")
flags.DEFINE_string("user_id", "test_user", "User ID for session operations.")
flags.DEFINE_string("session_id", None, "Session ID for operations.")
flags.DEFINE_bool("create", False, "Creates a new deployment.")
flags.DEFINE_bool("delete", False, "Deletes an existing deployment.")
flags.DEFINE_bool("list", False, "Lists all deployments.")
flags.DEFINE_bool("create_session", False, "Creates a new session.")
flags.DEFINE_bool("list_sessions", False, "Lists all sessions for a user.")
flags.DEFINE_bool("get_session", False, "Gets a specific session.")
flags.DEFINE_bool("send", False, "Sends a message to the deployed agent.")
flags.DEFINE_string(
    "message",
    "Shorten this message: Hello, how are you doing today?",
    "Message to send to the agent.",
)
flags.DEFINE_bool("deploy_laravel", False, "Creates a deployment specifically for Laravel/REST integration.")
flags.mark_bool_flags_as_mutual_exclusive(
    [
        "create",
        "deploy_laravel",
        "delete",
        "list",
        "create_session",
        "list_sessions",
        "get_session",
        "send",
    ]
)


def update_laravel_env(new_resource_id: str) -> None:
    """Updates the Laravel .env file with the new resource ID.

    Also ensures GOOGLE_CLOUD_PROJECT/LOCATION are present, since
    config/services.php reads those keys (not VERTEX_AI_*).
    """
    clean_id = new_resource_id.split("/")[-1]
    env_path = os.path.join(os.path.dirname(__file__), "..", "web-app", ".env")

    if not os.path.exists(env_path):
        print(f"Warning: Laravel .env not found at {env_path}")
        return

    required = {
        "VERTEX_AGENT_RESOURCE_ID": clean_id,
        "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        "GOOGLE_CLOUD_LOCATION": os.environ.get("GOOGLE_CLOUD_LOCATION", ""),
    }

    with open(env_path, "r") as f:
        lines = f.readlines()

    seen = set()
    with open(env_path, "w") as f:
        for line in lines:
            replaced = False
            for key, value in required.items():
                if line.startswith(f"{key}="):
                    f.write(f'{key}="{value}"\n')
                    seen.add(key)
                    replaced = True
                    break
            if not replaced:
                f.write(line)
        for key, value in required.items():
            if key not in seen and value:
                f.write(f'{key}="{value}"\n')

    print(f"Successfully synced Laravel .env (resource_id={clean_id})")


def deploy_laravel() -> None:
    """Deploys the agent wrapped in AdkApp for full REST compatibility.

    AdkApp automatically exposes create_session, list_sessions, get_session,
    delete_session, stream_query and async_stream_query — which is what the
    Laravel client calls. The previous custom wrapper only exposed `query`,
    so :create_session returned method-not-found.
    """
    print(f"Deploying agent '{root_agent.name}' via AdkApp...")

    adk_app = AdkApp(agent=root_agent, enable_tracing=True)

    remote_app = agent_engines.create(
        agent_engine=adk_app,
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]",
            "google-genai",
        ],
        extra_packages=["./admin_agent"],
    )
    print(f"Created Laravel-compatible app: {remote_app.resource_name}")

    update_laravel_env(remote_app.resource_name)


def list_deployments() -> None:
    """Lists all deployments."""
    deployments = agent_engines.list()
    if not deployments:
        print("No deployments found.")
        return
    print("Deployments:")
    for deployment in deployments:
        print(f"- {deployment.resource_name}")


def send_message(resource_id: str, user_id: str, session_id: str, message: str) -> None:
    """Sends a message to the deployed agent via stream_query and prints the full response."""
    remote_app = reasoning_engines.ReasoningEngine(resource_id)

    print(f"Sending message to session {session_id}:")
    print(f"Message: {message}")
    print("\nResponse:")

    final_text = ""
    citations = []
    for event in remote_app.stream_query(
        message=message,
        user_id=user_id,
        session_id=session_id,
    ):
        content = event.get("content") if isinstance(event, dict) else None
        if not content:
            continue
        for part in content.get("parts", []):
            if part.get("text"):
                final_text += part["text"]
            func_resp = part.get("function_response")
            if func_resp and func_resp.get("name") == "rag_query":
                data = func_resp.get("response", {})
                if data.get("status") == "success":
                    for res in data.get("results", []):
                        source = res.get("source_name") or res.get("source_uri")
                        if source and source not in citations:
                            citations.append(source)

    print(final_text.strip() or "[no text in response]")
    if citations:
        print("\nCitações:")
        for citation in citations:
            print(f"- {citation}")


def main(argv=None):
    """Main function that can be called directly or through app.run()."""
    if argv is None:
        argv = flags.FLAGS(sys.argv)
    else:
        argv = flags.FLAGS(argv)

    load_dotenv()

    project_id = (
        FLAGS.project_id if FLAGS.project_id else os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    location = FLAGS.location if FLAGS.location else os.getenv("GOOGLE_CLOUD_LOCATION")
    bucket = FLAGS.bucket if FLAGS.bucket else os.getenv("GOOGLE_CLOUD_STAGING_BUCKET")
    user_id = FLAGS.user_id

    if not project_id:
        print("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
        return
    elif not location:
        print("Missing required environment variable: GOOGLE_CLOUD_LOCATION")
        return
    elif not bucket:
        print("Missing required environment variable: GOOGLE_CLOUD_STAGING_BUCKET")
        return

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=bucket,
    )

    if FLAGS.deploy_laravel:
        deploy_laravel()
    elif FLAGS.list:
        list_deployments()
    elif FLAGS.send:
        if not FLAGS.resource_id:
            print("resource_id is required for send")
            return
        if not FLAGS.session_id:
            print("session_id is required for send")
            return
        send_message(FLAGS.resource_id, user_id, FLAGS.session_id, FLAGS.message)
    else:
        print("Please specify one of: --deploy_laravel, --list, or --send")


if __name__ == "__main__":
    app.run(main)
