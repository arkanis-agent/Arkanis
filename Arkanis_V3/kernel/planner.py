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

    SYSTEM_PROMPT = """SISTEMA OPERACIONAL ARKANIS V3 - KERNEL DE PROCESSAMENTO

Você é o Cérebro do ARKANIS V3, uma interface de inteligência operacional de elite especializada em engenharia de sistemas.

IDENTIDADE CENTRAL (SOUL):
{agent_identity}

REGRAS DE ENGENHARIA & ARQUITETURA:
1. DESENVOLVIMENTO DE SISTEMAS: Quando solicitado a criar ou desenvolver, PLANEJE uma estrutura completa de imediato.
   - Use 'create_directory' para pastas e 'write_file' para os arquivos.
   - NÃO PEÇA PERMISSÃO. NÃO DIGA "EU POSSO FAZER ISSO". FAÇA.
2. CONSTRUÇÃO MANDATÓRIA: Se o usuário pedir para "criar", "desenvolver" ou "fazer", o seu plano deve OBRIGATORIAMENTE incluir ferramentas de ação (write_file). 
   - Proibido usar apenas 'print_message' nesses casos. 
   - Respostas puramente conversacionais são consideradas falhas de sistema.
3. PRAGMATISMO: Seja direto. Se o usuário diz "Crie um script", você retorna o JSON com o script. Sem saudações. Sem redundâncias.
4. PIPING: Use {{ tool_name }} para passar resultados entre ferramentas.
5. SEGURANÇA: Nunca tente acessar diretórios fora do escopo permitido.

REGRAS DE FORMATO:
1. Responda APENAS em JSON no formato: [{{"tool": "nome_ferramenta", "args": {{"arg": "valor"}}}}]
2. NÃO use markdown blocks (```) se possível, retorne o JSON bruto.
3. Se não houver ferramentas úteis para o pedido, use 'print_message' com uma nota técnica concisa.

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
        """Loads the identity from IDENTITY.md or SOUL.md if they exist."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        identity_path = os.path.join(base_dir, "IDENTITY.md")
        soul_path = os.path.join(base_dir, "SOUL.md")
        
        target_path = identity_path if os.path.exists(identity_path) else soul_path
        
        if os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    identity = f.read().strip()
                rprint(f"[bold magenta][SOUL] Identity loaded from {os.path.basename(target_path)}[/bold magenta]")
                # Prepare against unintentional { } in markdown files that brake format()
                identity = identity.replace("{", "{{").replace("}", "}}")
                return identity
            except Exception as e:
                rprint(f"[bold red][SOUL] Failed to load identity: {str(e)}[/bold red]")
                
        return "Aja como um assistente amigável, natural e leal. Evite ser robótico ou formal demais. Trate o usuário como um parceiro."

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

    def _call_llm(self, system_prompt: str, user_input: str, task_hint: Optional[str] = None) -> str:
        """
        Calls the LLM Router for generation.
        Falls back to Mock Logic if all providers fails.
        """
        # Try LLM Router first (OpenRouter or Ollama)
        response = self.llm.generate(system_prompt=system_prompt, user_prompt=user_input, task_hint=task_hint)
        
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

    def plan(self, user_input: str, recent_context: str = "Nenhum histórico recente.", task_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """Main execution flow for planning."""
        inventory = self._get_tool_descriptions()
        
        # --- PREMIUM AESTHETICS INJECTION (Elite Engineering Mode) ---
        premium_directive = ""
        if task_hint == "engineering":
            premium_directive = "\n\n🔥 DIRETIVA DE DESIGN PREMIUM (MANDATÓRIA - QUALIDADE ELITE):\n" + \
                "- **ESTÉTICA DE ALTA FIDELIDADE**: Design ultra-moderno, 'Apple-style' ou 'SaaS Premium'.\n" + \
                "- **CSS OBRIGATÓRIO**: Use Tailwind CSS 4.0 ou Modern CSS.\n" + \
                "- **ELEMENTOS VISUAIS**: \n" + \
                "  * Graded backgrounds (ex: `bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900`)\n" + \
                "  * Glassmorphism (ex: `bg-white/10 backdrop-blur-md border border-white/20`)\n" + \
                "  * Soft Shadows (`shadow-2xl`), Micro-interações (`hover:scale-105 transition-all`)\n" + \
                "  * Fontes modernas (Sans-serif elegantes).\n" + \
                "- **REGRA DE OURO**: Proibido layouts básicos ou cinzas. Se for criar um card, que seja um card com hover dinâmico e bordas suaves.\n" + \
                "- **CONTEÚDO**: Use textos reais de marketing, não use 'Lorem Ipsum'.\n"

        system_prompt = self.SYSTEM_PROMPT.format(
            agent_identity=self.agent_identity,
            tool_inventory=inventory,
            recent_context=recent_context
        ) + premium_directive
        
        try:
            raw_response = self._call_llm(system_prompt, user_input, task_hint=task_hint)
            plan = self._parse_plan(raw_response)
            return plan
        except Exception as e:
            return [{"tool": "print_message", "args": {"message": f"Falha no Kernel Planner: {str(e)}"}}]
