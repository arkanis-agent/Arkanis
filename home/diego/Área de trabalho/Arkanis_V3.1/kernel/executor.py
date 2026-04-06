from typing import List, Dict, Any, Optional
import re
import json
from tools.registry import registry
from rich import print as rprint

# Pre-compiled regex pattern for performance (compile once, use many times)
PLACEHOLDER_PATTERN = re.compile(r'\\{\\{?\\s*(\\w+)\\s*\\}}?
')


class Executor:
    """
    Executes the planned steps using the registered tools.
    Supports Result Propagation (Piping) between steps using {{ tool_name }} syntax.
    """
    
    def _parse_datetime_result(self, result: Any) -> Any:
        """Flatten datetime results from JSON format if applicable."""
        if not isinstance(result, str):
            return result
        try:
            data = json.loads(result)
            if isinstance(data, dict) and "datetime" in data:
                return data.get("datetime", result)
        except json.JSONDecodeError:
            pass
        return result
    
    def _resolve_placeholders(self, args: Dict[str, Any], 
                               execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve {{ tool_name }} placeholders using execution context."""
        resolved_args = args.copy()
        for key, value in args.items():
            if isinstance(value, str):
                alias_map = {}
                for tool_name, tool_result in execution_context.items():
                    alias_map[tool_name] = tool_result
                    # Add alias without 'get_' prefix
                    alias_map[tool_name.replace('get_', '')] = tool_result
                
                def replace_func(match):
                    tool_name = match.group(1)
                    if tool_name in alias_map:
                        result = alias_map[tool_name]
                        if "datetime" in tool_name:
                            result = self._parse_datetime_result(result)
                        return str(result)
                    return match.group(0)
                
                resolved_args[key] = PLACEHOLDER_PATTERN.sub(replace_func, value)
        
        return resolved_args
    
    def execute_plan(self, plan: List[Dict[str, Any]]) -> List[Any]:
        results = []
        execution_context = {}  # Tracks results of tools in this plan
        
        rprint("\n[bold yellow]--- Iniciando Execução ---[/bold yellow]")
        
        for step in plan:
            tool_name = step.get("tool")
            args = step.get("args", {})
            
            # --- Resolve Placeholders for Current Step ---
            args = self._resolve_placeholders(args, execution_context)
            
            # --- Lazy Placeholder Resolution for Missing Tools ---
            if any(isinstance(v, str) and PLACEHOLDER_PATTERN.search(v) 
                   for v in args.values()):
                for key, value in args.items():
                    if isinstance(value, str):
                        missing_tools = PLACEHOLDER_PATTERN.findall(value)
                        for tool_id in missing_tools:
                            actual_tool = (registry.get_tool(tool_id) or 
                                         registry.get_tool(f"get_{tool_id}"))
                            if actual_tool and not actual_tool.arguments:
                                try:
                                    lazy_res = actual_tool.execute()
                                    if "datetime" in tool_id:
                                        lazy_res = self._parse_datetime_result(lazy_res)
                                    
                                    placeholder_pattern = re.compile(
                                        rf"\\{\\{\\{{?\\s*{re.escape(tool_id)}\\s*\\}}}}?
                                    )
                                    args[key] = placeholder_pattern.sub(
                                        str(lazy_res), value
                                    )
                                    break
                                except Exception as e:
                                    rprint(f"[red]⚠️ Lazy resolver falhou: {e}[/red]")
                                    break
                            
            actual_tool = registry.get_tool(tool_name)
            if actual_tool:
                rprint(f"[bold yellow][Executor] Executando:[/bold yellow] {tool_name}")
                try:
                    result = actual_tool.execute(**args)
                    rprint(f"[bold green][Executor] Concluído:[/bold green] {tool_name}")
                    
                    # Store result for potential piping to next steps
                    execution_context[tool_name] = result
                    results.append(result)
                except Exception as e:
                    error_msg = f"Error: Tool '{tool_name}' crashed -> {str(e)}"
                    rprint(f"[bold red][Executor] Erro na ferramenta {tool_name}:[/bold red] {error_msg}")
                    results.append(error_msg)
            else:
                error_msg = f"Error: Tool '{tool_name}' not found."
                rprint(f"[bold red][Executor] Erro:[/bold red] {error_msg}")
                results.append(error_msg)
        
        rprint("[bold green]--- Execução Finalizada ---[/bold green]\n")
        return results
