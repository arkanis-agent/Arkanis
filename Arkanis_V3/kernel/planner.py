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
   - IMPORTANTE: Para usar {{ get_current_datetime }} ou qualquer ferramenta como placeholder, você DEVE EXECUTAR essa ferramenta no MESMO PLANO antes de usá-la.
5. SEGURANÇA: Nunca tente acessar diretórios fora do escopo permitido.
6. FERRAMENTAS REAIS: NUNCA use ferramentas que não estão no inventário abaixo. 
   - Se precisar modificar um pequeno trecho de código, use 'replace_file_content'. 
   - 'write_file' deve ser usado apenas para arquivos novos ou substituição total.
   - Proibido alucinar funções inexistentes.

WEB INTELLIGENCE — ROTEAMENTO OBRIGATÓRIO (CONTEXTO ATUAL: ANO 2026):
7. DADOS EM TEMPO REAL (cripto, câmbio, esportes, clima): Use SEMPRE as ferramentas especializadas:
   - Preços de moedas/criptos → 'get_crypto_price' ou 'get_exchange_rate'
   - Resultados de jogos/esportes → 'get_sports_score'
   - Clima e temperatura → 'get_weather'
   - NUNCA faça 'web_search' para dados que essas ferramentas já resolvem diretamente.
8. BUSCA DE INFORMAÇÕES (notícias, pesquisa geral): Use 'web_search' primeiro. 
   - Se a busca retornar "Nenhum resultado", NÃO INVENTE notícias. Diga que não encontrou.
   - Lembre-se: Estamos em 2026. Se não houver dados de 2026 na busca, não use dados de 2022 (como Biden presidente) como se fossem atuais.
9. LEITURA DE PÁGINA (conteúdo estático, artigos, APIs): Use 'fetch_url'. Funciona com headers reais de Chrome.
10. ACESSO A SITES COM JAVASCRIPT / LOGIN / FORMULÁRIOS: Use a sequência correta:
    a. 'browser_open' para abrir a página (SEMPRE primeiro)
    b. 'browser_wait' para aguardar conteúdo carregar
    c. 'browser_fill' para preencher campos
    d. 'browser_click' para clicar botões
    e. 'browser_submit' para submeter formulários (Enter)
    f. 'browser_extract' para ler o resultado
    - Use 'browser_screenshot' para confirmar o estado visual se necessário.
    - NUNCA use browser_ sem chamar 'browser_open' primeiro.
11. MONITORAMENTO CONTÍNUO: Para monitorar se uma página mudou, use 'page_monitor'. Ideal para verificar agenda de consultório, disponibilidade de produto, etc.

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
        """
        ULTRA-ROBUST Arkanis V3.1 JSON Parser.
        Extracts tool plans even from malformed markdown, conversational noise, or multiple JSON blocks.
        """
        # 1. CLEANING: Remove markdown triple backticks and excessive whitespace
        clean_input = re.sub(r'```json\n?|```\n?|```', '', raw_response).strip()
        
        # 2. ATTEMPT 1: Direct JSON parsing (The perfect scenario)
        try:
            parsed = json.loads(clean_input)
            if isinstance(parsed, dict): return [parsed]
            if isinstance(parsed, list): return parsed
        except: pass

        # 3. ATTEMPT 2: Array Extraction (Looking for [...] in the noise)
        try:
            # Find the FIRST '[' and LAST ']'
            start = clean_input.find('[')
            end = clean_input.rfind(']')
            if start != -1 and end != -1 and end > start:
                array_str = clean_input[start:end+1]
                # Further sanitize inner markdown if present
                array_str = re.sub(r'```json\n?|```\n?|```', '', array_str).strip()
                parsed = json.loads(array_str)
                if isinstance(parsed, list): return parsed
                if isinstance(parsed, dict): return [parsed]
        except: pass

        # 4. ATTEMPT 3: Object Fragment Extraction (Brace Counting)
        # Handle cases where multiple objects are given without an array or are deeply nested
        try:
            valid_tools = []
            stack = 0
            start_idx = -1
            for i, char in enumerate(clean_input):
                if char == '{':
                    if stack == 0: start_idx = i
                    stack += 1
                elif char == '}':
                    stack -= 1
                    if stack == 0 and start_idx != -1:
                        obj_str = clean_input[start_idx:i+1]
                        try:
                            # Basic validation: must contain "tool"
                            if '"tool"' in obj_str or "'tool'" in obj_str:
                                tool_obj = json.loads(obj_str)
                                if isinstance(tool_obj, dict) and "tool" in tool_obj:
                                    valid_tools.append(tool_obj)
                        except: pass
            
            if valid_tools:
                return valid_tools
        except: pass

        # 5. FINAL FALLBACK: Print Message
        return [{"tool": "print_message", "args": {"message": "[RELATÓRIO TÉCNICO] Erro crítico no parsing do Plano JSON. O modelo não gerou uma estrutura válida para execução de engenharia."}}]

    def plan(self, user_input: str, recent_context: str = "Nenhum histórico recente.", task_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """Main execution flow for planning."""
        inventory = self._get_tool_descriptions()
        
        # --- PREMIUM AESTHETICS INJECTION (Elite Engineering Mode) ---
        premium_directive = ""
        ui_keywords = ['layout', 'tela', 'interface', 'dashboard', 'frontend', 'site', 'css', 'html', 'ui', 'ux', 'visual', 'landing page', 'page', 'página', 'crm', 'web', 'sistema']
        is_ui_task = any(kw in user_input.lower() for kw in ui_keywords) or task_hint == "engineering"
        
        if is_ui_task:
            premium_directive = "\n\n🔥 DIRETIVA DE DESIGN DE INTERFACE PREMIUM (MANDATÓRIA PARA AÇÕES WEB/UI):\n" + \
                "- VOCÊ DEVE CRIAR UM DESIGN ULTRA-MODERNO. ABOMINAMOS layouts básicos, cinzas ou 'anos 90'.\n" + \
                "- **ESTRUTURA OBRIGATÓRIA**: Sempre importe as seguintes bibliotecas no HTML:\n" + \
                "  1. Tailwind CSS via CDN: `<script src=\"https://cdn.tailwindcss.com\"></script>`\n" + \
                "  2. Fonte 'Inter' e 'Outfit' do Google Fonts.\n" + \
                "  3. FontAwesome para ícones: `<link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css\">`\n" + \
                "- **TAILWIND CONFIG**: Adicione `<script>tailwind.config = { theme: { extend: { fontFamily: { sans: ['Inter', 'sans-serif'], display: ['Outfit', 'sans-serif'] } } } };</script>`\n" + \
                "- **ELEMENTOS ESTÉTICOS EXIGIDOS**: \n" + \
                "  * Cores modernas e paletas combinadas (ex: fundos escuros slate/gray-900, gradients com blue-600/purple-600).\n" + \
                "  * **Glassmorphism**: Use `backdrop-blur-xl bg-white/10 border border-white/20` para cards e navbars se estiver no escuro.\n" + \
                "  * **Sombras Suaves & Bordas Arredondadas**: Sempre use `rounded-2xl` ou `rounded-3xl` com `shadow-xl` ou `shadow-2xl`.\n" + \
                "  * **Micro-animações**: Hover obrigatório em botões e cards (`transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:scale-105`).\n" + \
                "  * **Tipografia**: Use títulos com `font-display`, peso `font-bold` ou `font-extrabold`, e gradientes de texto (`bg-clip-text text-transparent bg-gradient-to-r`).\n" + \
                "- **CONTEÚDO FINAL**: Não deixe o HTML vazio com 'Lorem Ipsum'. Gere dados fictícios que pareçam um sistema real operando na produção.\n"

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
