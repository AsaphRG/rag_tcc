# Documentação Técnica: Sistema de Agentes RAG com Vertex AI

## 1. Visão Geral
Este sistema utiliza o **Google Agent Development Kit (ADK)** para criar agentes inteligentes que operam sobre o **Vertex AI RAG (Retrieval-Augmented Generation)**. O objetivo é permitir a gestão de documentos e a recuperação de informações semânticas em larga escala, utilizando modelos generativos (Gemini) para sintetizar respostas precisas baseadas em contextos privados.

## 2. Arquitetura do Sistema

O projeto é dividido em dois agentes principais que compartilham uma base de ferramentas modulares:

*   **AdminAgent (Resina Data Consultant):** Agente especializado com permissões completas de gestão de dados e ferramentas de comunicação (e-mail). Focado no atendimento em Português Brasileiro.
*   **RAGAgent:** Agente padrão para operações de CRUD em corpora e documentos.

### Fluxo de Dados
1.  **Ingestão:** Os documentos são apontados (URLs do Google Drive ou caminhos GCS) e processados pela ferramenta `add_data`.
2.  **Indexação:** O Vertex AI processa os arquivos, gera embeddings (usando `text-embedding-005`) e os armazena em um `ragCorpus`.
3.  **Recuperação:** A ferramenta `rag_query` realiza uma busca vetorial no corpus para encontrar os trechos mais relevantes.
4.  **Geração:** O modelo `gemini-2.5-flash` recebe a pergunta e o contexto recuperado para gerar a resposta final.

## 3. Especificação das Ferramentas (Tools)

As ferramentas são implementadas de forma modular em `admin_agent/tools/` e `rag_agent/tools/`.

### `rag_query`
Realiza a busca semântica e geração de resposta.
*   **Mecanismo:** Utiliza `vertexai.rag.query`.
*   **Parâmetros:**
    *   `query` (string): Pergunta do usuário.
    *   `corpus_name` (string): Nome do recurso no GCP.
*   **Configurações Padrão:** `top_k=3`, `distance_threshold=0.5`.

### `add_data`
Faz o upload ou vinculação de novos dados ao corpus.
*   **Suporte:** Google Cloud Storage (GCS) e Google Drive.
*   **Processo:** Utiliza `rag.import_files` de forma assíncrona ou síncrona dependendo da configuração.

### `create_corpus`
Provisiona um novo repositório de documentos no Vertex AI.
*   **Configuração de Embedding:** `text-embedding-005`.
*   **Parâmetros:** `display_name` definido pelo usuário.

### `send_email` (Exclusivo AdminAgent)
Ferramenta de integração externa para notificação.
*   **Funcionalidade:** Permite o envio de comunicados sobre incidentes ou respostas de consultas para usuários específicos.

## 4. Configuração e Variáveis de Ambiente

O arquivo `config.py` centraliza os parâmetros técnicos. As seguintes variáveis de ambiente são críticas:

| Variável | Descrição |
| :--- | :--- |
| `GOOGLE_CLOUD_PROJECT` | ID do projeto no Google Cloud. |
| `GOOGLE_CLOUD_LOCATION` | Região do Vertex AI (ex: `us-central1`). |
| `DEFAULT_CHUNK_SIZE` | Tamanho do fragmento de texto (padrão: 512 tokens). |
| `DEFAULT_EMBEDDING_MODEL` | Modelo de embedding (`text-embedding-005`). |

## 5. Implementação de Segurança

O sistema implementa filtros de segurança rigorosos através de `SafetySetting` do SDK da Google GenAI:

*   **Categorias Bloqueadas:** Conteúdo perigoso, assédio, discurso de ódio, conteúdo sexualmente explícito e tentativas de *jailbreak*.
*   **Threshold:** `BLOCK_ONLY_HIGH` (ajustável conforme necessidade de precisão).
*   **Diretiva de Sistema:** O agente possui instruções explícitas (System Instructions) para recusar tópicos sensíveis como política, religião e segurança pública.

## 6. Gestão de Estado (Tool Context)

O sistema utiliza o `ToolContext` do ADK para manter a persistência durante a sessão:
*   **`current_corpus`:** Armazena o corpus que o usuário está manipulando no momento, evitando que ele precise repetir o nome do recurso em cada comando.
*   **Mapeamento de Nomes:** A função `get_corpus_resource_name` em `utils.py` traduz nomes amigáveis (Display Names) para o formato canônico exigido pela API do Google (`projects/.../locations/.../ragCorpora/...`).

## 7. Requisitos de Autenticação

Para operação em ambiente de desenvolvimento:
1.  **ADC (Application Default Credentials):** O ambiente deve estar autenticado via `gcloud auth application-default login`.
2.  **IAM Roles:** A conta de serviço ou usuário deve possuir as permissões:
    *   `roles/aiplatform.user`
    *   `roles/storage.objectViewer` (para ingestão de GCS)
