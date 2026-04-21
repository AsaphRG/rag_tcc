import os
import sys

import vertexai
from absl import app, flags
from dotenv import load_dotenv
from vertexai import agent_engines
from vertexai.preview import reasoning_engines

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

class AgentWrapper:
    """Wrapper class that receives the root_agent and exposes the query method for REST."""
    def __init__(self, agent):
        self.agent = agent
        self._session_service = None

    def set_up(self):
        """Called by the Reasoning Engine on the server side."""
        from google.adk.sessions.in_memory_session_service import InMemorySessionService
        self._session_service = InMemorySessionService()

    def query(self, message: str, user_id: str = "laravel_user", session_id: str = "laravel_session") -> dict:
        """
        Entry point for the :query REST endpoint with native fallback for stability.
        """
        import sys
        import os
        
        try:
            from google.adk.runners import Runner
            from google.adk.sessions.in_memory_session_service import InMemorySessionService
            
            if self._session_service is None:
                self._session_service = InMemorySessionService()
            
            final_text = ""
            citations = []
            
            # 1. Tentativa via Runner do ADK (Motor completo com ferramentas)
            runner = Runner(
                agent=self.agent, 
                app_name=self.agent.name, 
                session_service=self._session_service
            )
            
            try:
                for event in runner.run(input=message, user_id=user_id, session_id=session_id):
                    if hasattr(event, "content") and event.content:
                        parts = event.content.get("parts", [])
                        for part in parts:
                            if "text" in part:
                                final_text += part["text"]
                            
                            if "function_response" in part:
                                f_resp = part["function_response"]
                                if f_resp.get("name") == "rag_query":
                                    resp_data = f_resp.get("response", {})
                                    if resp_data.get("status") == "success":
                                        results = resp_data.get("results", [])
                                        for res in results:
                                            source = res.get("source_name") or res.get("source_uri")
                                            if source and source not in citations:
                                                citations.append(source)
            except Exception as adk_err:
                print(f"Erro no loop ADK: {adk_err}", file=sys.stderr)

            # 2. FALLBACK: Se o ADK falhar em gerar texto, usamos a API nativa do Gemini
            if not final_text:
                print("Iniciando fallback nativo...", file=sys.stderr)
                from google import genai
                from google.genai import types
                
                client = genai.Client(
                    vertexai=True, 
                    project=os.environ.get("GOOGLE_CLOUD_PROJECT"), 
                    location=os.environ.get("GOOGLE_CLOUD_LOCATION")
                )
                
                res = client.models.generate_content(
                    model=self.agent.model,
                    contents=message,
                    config=types.GenerateContentConfig(
                        system_instruction=self.agent.instruction,
                        temperature=0.2
                    )
                )
                final_text = res.text if res.text else "[Agente indisponível no momento]"

            return {
                "content": final_text.strip(),
                "citations": citations
            }
        except Exception as e:
            import traceback
            print(f"ERRO CRÍTICO NO WRAPPER: {str(e)}", file=sys.stderr)
            return {
                "content": f"Erro interno: {str(e)}",
                "traceback": traceback.format_exc(),
                "citations": [],
                "error": True
            }

def update_laravel_env(new_resource_id: str) -> None:
    """Updates the Laravel .env file with the new resource ID."""
    # O ID vem no formato projects/.../locations/.../reasoningEngines/ID
    clean_id = new_resource_id.split("/")[-1]
    env_path = os.path.join(os.path.dirname(__file__), "..", "web-app", ".env")
    
    if not os.path.exists(env_path):
        print(f"Warning: Laravel .env not found at {env_path}")
        return

    with open(env_path, "r") as f:
        lines = f.readlines()

    with open(env_path, "w") as f:
        found = False
        for line in lines:
            if line.startswith("VERTEX_AGENT_RESOURCE_ID="):
                f.write(f'VERTEX_AGENT_RESOURCE_ID="{clean_id}"\n')
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f'\nVERTEX_AGENT_RESOURCE_ID="{clean_id}"\n')
    
    print(f"Successfully updated Laravel .env with resource ID: {clean_id}")

def deploy_laravel() -> None:
    """Creates a new deployment 'inserting' the root_agent into the wrapper for REST compatibility."""
    print(f"Deploying agent '{root_agent.name}' with Laravel/REST compatibility wrapper...")
    
    # Create the instance of the wrapper with your root_agent
    wrapper_instance = AgentWrapper(root_agent)
    
    remote_app = agent_engines.create(
        agent_engine=wrapper_instance,
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]",
            "google-genai",
        ],
        extra_packages=["./admin_agent"],
    )
    print(f"Created Laravel-compatible app: {remote_app.resource_name}")
    
    # Atualiza o .env automaticamente
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
    """Sends a message to the deployed agent."""
    remote_app = reasoning_engines.ReasoningEngine(resource_id)

    print(f"Sending message to session {session_id}:")
    print(f"Message: {message}")
    print("\nResponse:")
    
    # Usamos .query() que é o método padrão exposto pelo Reasoning Engine remoto
    response = remote_app.query(
        user_id=user_id,
        session_id=session_id,
        message=message,
    )
    
    # Trata a resposta baseada no formato do Wrapper
    if isinstance(response, dict) and "content" in response:
        print(response["content"])
        if response.get("citations"):
            print("\nCitações:")
            for citation in response["citations"]:
                print(f"- {citation}")
    else:
        print(f"DEBUG: Resposta bruta: {response}")


def main(argv=None):
    """Main function that can be called directly or through app.run()."""
    # Parse flags first
    if argv is None:
        argv = flags.FLAGS(sys.argv)
    else:
        argv = flags.FLAGS(argv)

    load_dotenv()

    # Now we can safely access the flags
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
