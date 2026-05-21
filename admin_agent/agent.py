from google.adk.agents import Agent
from google.genai.types import HarmCategory, HarmBlockThreshold, SafetySetting, GenerateContentConfig

from .tools.add_data import add_data
from .tools.create_corpus import create_corpus
from .tools.delete_corpus import delete_corpus
from .tools.delete_document import delete_document
from .tools.get_corpus_info import get_corpus_info
from .tools.list_corpora import list_corpora
from .tools.rag_query import rag_query
from .tools.send_email import send_email

safety_settings = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
    )
]

root_agent = Agent(
   name="admin_agent",
   # gemini-2.0-flash-001 está disponível em us-west1 e é o modelo recomendado
   # pelo ADK 1.29+. gemini-1.5-flash está em deprecation path.
   model="gemini-2.0-flash-001",
   generate_content_config=GenerateContentConfig(
      temperature=0.2,
      top_p=0.95,
      safety_settings=safety_settings
   ),
   description="Prowise RAG Agent",
   tools=[
      rag_query,
      list_corpora,
      create_corpus,
      add_data,
      get_corpus_info,
      delete_corpus,
      delete_document,
      send_email,
   ],
   instruction="""
   # 🧠 Prowise RAG Agent
   Você é um representante da Prowise. Sua missão é ajudar usuários consultando as bases de documentos da empresa.
   Responda sempre em Português Brasileiro de forma profissional e clara.
   Use a ferramenta rag_query sempre que precisar de informações específicas sobre a Prowise.
   """,
)
