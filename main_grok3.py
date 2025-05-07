from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from pyngrok import ngrok
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
import json
import re
import threading
import subprocess
import time
import unicodedata
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

esquema_banco = {}
prompt_template_sql = PromptTemplate(
    input_variables=["input_text", "schema_info"],
    template="""
    You are a SQL expert tasked with converting natural language queries into SQL SELECT statements. Your goal is to generate accurate SQL queries based on the provided database schema and user input. Follow the instructions carefully to ensure the output is correct and reliable.

    **Database Schema**:
    {schema_info}

    **User Query**:
    {input_text}

    **Instructions**:
    1. Analyze the user query and match it to the tables and columns in the provided schema.
    2. Generate a SQL SELECT statement that retrieves the requested data. Only use tables and columns from the schema.
    3. If the query is ambiguous or cannot be mapped to the schema, return: ```I don't know.```
    4. If the query is unrelated to generating a SQL query (e.g., asking for explanations or non-query tasks), return: ```I don't know.```
    5. Table names are duplicated due to Django conventions. For example, use `usuario_usuario` instead of `usuario`.
    6. Most table and column names are in Brazilian Portuguese and may contain accents (e.g., `usuário`, `código`). Normalize accents to their non-accented equivalents (e.g., `usuario`, `codigo`) when matching to the schema.
    7. Only generate SELECT statements. Do not use INSERT, UPDATE, DELETE, or other SQL commands.
    8. Output the SQL query inside triple backticks (```) with no additional comments, explanations, or text outside the backticks.
    9. Remove any trailing semicolons from the query.
    10. If the query involves aggregation (e.g., "total", "sum", "average"), use appropriate SQL functions like SUM, AVG, or COUNT.
    11. If the query involves filtering (e.g., "where", "for"), use WHERE clauses with exact column names from the schema.
    12. If the query involves sorting (e.g., "ordered by", "highest"), use ORDER BY with appropriate ASC or DESC.
    """
)

# Normalize accents in text
def normalize_accents(text: str) -> str:
    """Remove accents from text to match schema without diacritics."""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

# Update schema context
def atualiza_contexto(json_str):
    global esquema_banco
    try:
        logger.info('Updating schema context')
        if isinstance(json_str, dict):
            esquema_banco = json_str
        else:
            esquema_banco = json.loads(json_str)
        if not esquema_banco:
            raise ValueError("Schema is empty or invalid")
        logger.info('Schema updated successfully: %s', esquema_banco)
        return 'Contexto atualizado com sucesso!'
    except Exception as e:
        logger.error('Error updating schema: %s', str(e))
        return f"Erro ao atualizar o contexto: {str(e)}"

# Generate SQL response with retry logic
def gera_resposta(prompt_usuario: str, max_retries: int = 3) -> str:
    logger.info('Processing user query: %s', prompt_usuario)
    if not esquema_banco:
        logger.error('No schema provided')
        return "Erro: Nenhum esquema de banco de dados fornecido."
    
    # Normalize accents in user input
    normalized_prompt = normalize_accents(prompt_usuario)
    
    for attempt in range(max_retries):
        try:
            llm_response = sql_chain.invoke({
                "input_text": normalized_prompt,
                "schema_info": json.dumps(esquema_banco, ensure_ascii=False)
            })
            logger.info('LLM response: %s', llm_response)
            sql_query = extrair_consulta_sql(llm_response)
            logger.info('Extracted SQL query: %s', sql_query)
            return sql_query
        except Exception as e:
            logger.warning('Attempt %d failed: %s', attempt + 1, str(e))
            if attempt == max_retries - 1:
                logger.error('Max retries reached. Error: %s', str(e))
                return f"Erro ao gerar resposta: {str(e)}"
            time.sleep(1)  # Wait before retrying

def extrair_consulta_sql(resposta_llm: str) -> str:
    """Extract and format SQL query from LLM response."""
    try:
        padrao = r'```(?:sql)?\s*(.*?)\s*```'
        match = re.search(padrao, resposta_llm, re.DOTALL)
        if match:
            consulta_sql = match.group(1).strip()
            if consulta_sql.upper().startswith('SQL'):
                consulta_sql = consulta_sql[3:].strip()
            if not consulta_sql.upper().startswith('SELECT'):
                return "Erro: A consulta retornada não é um SELECT válido."
            return consulta_sql.rstrip(';')
        return "Erro: Não foi possível gerar uma consulta com essas informações."
    except Exception as erro:
        logger.error('Error processing SQL query: %s', str(erro))
        return f"Erro: Falha ao processar a consulta SQL - {str(erro)}"

# Run Ollama server
def run_ollama_serve():
  subprocess.Popen(["ollama", "serve"])

thread = threading.Thread(target=run_ollama_serve)
thread.start()
time.sleep(5)

# Load schema from JSON file
try:
    with open("esquema_banco.json", "r", encoding='utf-8') as file:
        esquema_banco = json.load(file)
        atualiza_contexto(esquema_banco)
except FileNotFoundError:
    logger.error("Schema file 'esquema_banco.json' not found")
except json.JSONDecodeError as e:
    logger.error("Invalid JSON in schema file: %s", str(e))

# Initialize LLM and chain
llm = OllamaLLM(model="llama3.1")
sql_chain = prompt_template_sql | llm

# Set up XML-RPC server
class ManipuladorDeRequisicoes(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/RPC2",)

server = SimpleXMLRPCServer(
    ("0.0.0.0", 1346),
    requestHandler=ManipuladorDeRequisicoes,
    allow_none=True
)

# Register functions
server.register_function(atualiza_contexto, "atualiza_contexto")
server.register_function(gera_resposta, "gera_resposta")

# Set up ngrok tunnel
try:
    url_publica = ngrok.connect(1346, bind_tls=True).public_url
    logger.info("Public URL: %s", url_publica)
except Exception as e:
    logger.error("Failed to connect with ngrok: %s", str(e))
    raise

# Start server
logger.info("Starting XML-RPC server")
server.serve_forever()