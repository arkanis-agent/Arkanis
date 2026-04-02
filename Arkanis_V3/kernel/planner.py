import json
import re
import os
from typing import List, Dict, Any, Optional
from tools.registry import registry
from core.llm_client import LLMClient
from rich import print as rprint

class Planner:
    """
    PLANNER V3: AI-Powered Brain for ARKANIS OS.
    Translates natural language into a structured JSON plan using OpenRouter.
    """

    SYSTEM_PROMPT = """
SISTEMA OPERACIONAL ARKANIS V3 - KERNEL DE PROCESSAMENTO

Você é o Cérebro do ARKANIS V3, uma interface de inteligência operacional.

IDENTIDADE CENTRAL (SOUL):
{agent_identity}

REGRAS CRÍTICAS:
1. Responda APENAS em JSON no formato: [{{"tool": "nome_ferramenta", "args": {{"arg": "valor"}}}}]
2. Use APENAS ferramentas cadastradas no registro oficial abaixo.
3. Se o input for vago, use a ferramenta de feedback ou planeje o passo inicial.
4. Mantenha a saída limpa e técnica, adaptando as respostas (args) ao caráter da IDENTIDADE acima.
5. Utilize o CONTEXTO RECENTE para entender referências (ex: "o que eu pedi antes?").
6. PIPING: Para usar o resultado de uma ferramenta na seguinte, use o nome dela em chaves: {{ tool_name }}. O Executor substituirá pelo valor real.
7. TOOL CHAINING: Para tarefas complexas, prefira múltiplos passos menores. 
   Exemplo: 1. fetch_url -> 2. ask_llm (instruction="resuma", text_content="{{ fetch_url }}") -> 3. write_file.
8. Use 'ask_llm' para processar, filtrar ou resumir dados textuais obtidos por outras ferramentas antes de salvá-los ou exibi-los.
9. Se o usuário mencionar "hoje", "agora", "data atual" ou "hora", use OBRIGATORIAMENTE a ferramenta 'get_current_datetime' no início do seu plano e use {{ get_current_datetime }} nos passos seguintes.
10. Use 'list_files' para explorar o diretório antes de agir se o alvo for incerto.
11. Use 'file_exists' antes de ler ou escrever se precisar confirmar a existência de um arquivo.
12. Use 'read_file' para obter o conteúdo de arquivos solicitados pelo usuário.
37. Use 'web_search' for any queries about current events, news, weather, or generalized internet search. This is the OBRIGATORY first step for any search task.
38. Use 'fetch_url' ONLY when you have a specific, validated URL (usually obtained from web_search results). NEVER guess or fabricate URLs.
39. BROWSER AUTOMATION: Use 'browser_open' followed by 'browser_click', 'browser_fill' and 'browser_extract' for complex multi-step web interactions.
40. HTTP API: Use 'http_get' and 'http_post' for technical data consumption.
41. Rule: DO NOT fabricate tool results or error codes (404/500). If a tool fails, report the failure exactly as is.
42. Rule: DO NOT use placeholders like [key point] or [Summarized point]. Be factual.

FERRAMENTAS DISPONÍVEIS:
{tool_inventory}

CONTEXTO RECENTE:
{recent_context}

FORMATO EXIGIDO:
[
    {{
        "tool": "tool_name",
        "args": {{
            "param": "value"
        }}
    }}
]
"""

    def __init__(self, api_key: Optional[str] = None):
        self.registry = registry
        # Initialize the real LLM client
        self.llm = LLMClient(api_key=api_key)
        self.agent_identity = self._load_soul()

    def _load_soul(self) -> str:
        """Loads the identity from SOUL.md if it exists."""
        soul_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SOUL.md")
        if os.path.exists(soul_path):
            try:
                with open(soul_path, "r", encoding="utf-8") as f:
                    identity = f.read().strip()
                rprint("[bold magenta][SOUL] Identity loaded[/bold magenta]")
                # Prepare against unintentional { } in markdown files that brake format()
                identity = identity.replace("{", "{{").replace("}", "}}")
                return identity
            except Exception as e:
                rprint(f"[bold red][SOUL] Failed to load identity: {str(e)}[/bold red]")
                
        return "Aja como um assistente padrão. Nenhum arquivo SOUL.md foi encontrado."

    def _get_tool_descriptions(self) -> str:
        """Dynamically fetch tool metadata from the registry."""
        try:
            tools = self.registry.get_all_tools()
        except AttributeError:
            # Fallback se a branch do registro estiver desatualizada
            tools = list(self.registry._tools.values())
            
        formatted_list = []
        for tool in tools:
            args_str = json.dumps(tool.arguments, ensure_ascii=False)
            formatted_list.append(f"- {tool.name}: {tool.description} | Args: {args_str}")
        return "\n".join(formatted_list)

    def _call_llm(self, system_prompt: str, user_input: str) -> str:
        """
        Calls the LLM Router for generation.
        Falls back to Mock Logic if all providers fails.
        """
        # Try LLM Router first (OpenRouter or Ollama)
        response = self.llm.generate(system_prompt=system_prompt, user_prompt=user_input)
        
        if response and "[Error" not in response:
            return response
            
        # --- FALLBACK: show real error to user ---
        print(f"[Planner] LLM failed: {response}")
        import json as _json
        error_detail = str(response or "sem resposta do modelo")
        if "404" in error_detail:
            msg = "Modelo indisponível (404). Esse modelo não tem endpoints ativos no OpenRouter. Selecione outro modelo no menu superior."
        elif "429" in error_detail:
            msg = "Modelo com rate limit (429). Tente novamente em alguns segundos ou selecione outro modelo."
        elif "401" in error_detail:
            msg = "Chave de API inválida ou sem créditos (401). Verifique sua chave do OpenRouter em Providers / APIs."
        elif "Governor" in error_detail:
            msg = "Limite de chamadas por minuto atingido. Aguarde alguns segundos e tente novamente."
        else:
            msg = f"O modelo retornou um erro: {error_detail[:120]}. Selecione outro modelo no menu superior."
        return _json.dumps([{"tool": "print_message", "args": {"message": msg}}])

    def _parse_plan(self, raw_response: str) -> List[Dict[str, Any]]:
        """Safely parse JSON from LLM response with RegEx fallback."""
        try:
            # Clean possible markdown code blocks
            clean_json = re.sub(r'```json\n?|\n?```', '', raw_response).strip()
            parsed = json.loads(clean_json)
            
            # Ensure the result is always a list for the executor
            if isinstance(parsed, dict):
                return [parsed]
            if not isinstance(parsed, list):
                return []
            return parsed
        except (json.JSONDecodeError, TypeError):
            # Fallback patterns if JSON is slightly malformed
            match = re.search(r'\[.*\]', raw_response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except: pass
            
            return [{"tool": "print_message", "args": {"message": "Erro crítico no parsing do Plano JSON."}}]

    def plan(self, user_input: str, recent_context: str = "Nenhum histórico recente.") -> List[Dict[str, Any]]:
        """Main execution flow for planning."""
        inventory = self._get_tool_descriptions()
        system_prompt = self.SYSTEM_PROMPT.format(
            agent_identity=self.agent_identity,
            tool_inventory=inventory,
            recent_context=recent_context
        )
        
        try:
            raw_response = self._call_llm(system_prompt, user_input)
            plan = self._parse_plan(raw_response)
            return plan
        except Exception as e:
            return [{"tool": "print_message", "args": {"message": f"Falha no Kernel Planner: {str(e)}"}}]
