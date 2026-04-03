from typing import List, Dict, Any
from tools.registry import registry
from rich import print as rprint

class Executor:
    """
    Executes the planned steps using the registered tools.
    Supports Result Propagation (Piping) between steps using {{ tool_name }} syntax.
    """
    def execute_plan(self, plan: List[Dict[str, Any]]) -> List[str]:
        results = []
        execution_context = {}  # Tracks results of tools in this plan
        
        rprint("\n[bold yellow]--- Iniciando Execução ---[/bold yellow]")
        for step in plan:
            tool_name = step.get("tool")
            args = step.get("args", {})
            
            # --- Result Propagation Logic ---
            import re
            for key, value in args.items():
                if isinstance(value, str):
                    for prev_tool, prev_result in execution_context.items():
                        # Pattern to catch {tool}, {{tool}}, { tool }, {{ tool }}
                        # Also catches the alias without 'get_'
                        alias = prev_tool.replace('get_', '')
                        pattern = rf"{{{{?\s*({re.escape(prev_tool)}|{re.escape(alias)})\s*}}}}?"
                        
                        def replace_func(match):
                            processed_result = prev_result
                            # Specific flattening for get_current_datetime
                            if prev_tool == "get_current_datetime" and isinstance(prev_result, str):
                                try:
                                    import json
                                    data = json.loads(prev_result)
                                    processed_result = data.get("datetime", prev_result)
                                except: pass
                            return str(processed_result)

                        args[key] = re.sub(pattern, replace_func, value)
            
            # --- LAZY PLACEHOLDER RESOLUTION (For tools called via {{}} but NOT in the plan) ---
            if isinstance(args.get(key), str):
                # Search for any remaining {{ tool }} that were not in execution_context
                missing_placeholders = re.findall(r"{{{{?\s*(\w+)\s*}}}}?", args[key])
                for tool_id in missing_placeholders:
                    # If it's a simple tool (no required args), try lazy execution
                    actual_tool = registry.get_tool(tool_id) or registry.get_tool(f"get_{tool_id}")
                    if actual_tool and not actual_tool.arguments:
                        try:
                            lazy_res = actual_tool.execute()
                            # Flatten if it's datetime
                            if "datetime" in tool_id:
                                try:
                                    import json
                                    data = json.loads(lazy_res)
                                    lazy_res = data.get("datetime", lazy_res)
                                except: pass
                            
                            pattern = rf"{{{{?\s*{re.escape(tool_id)}\s*}}}}?"
                            args[key] = re.sub(pattern, str(lazy_res), args[key])
                        except: pass
            
            tool = registry.get_tool(tool_name)
            if tool:
                rprint(f"[bold yellow][Executor] Executando:[/bold yellow] {tool_name}")
                try:
                    # Resolve any nested dicts in args as well if they contain placeholders
                    result = tool.execute(**args)
                    rprint(f"[bold green][Executor] Concluído:[/bold green] {tool_name}")
                    
                    # Store result for potential piping to next steps
                    execution_context[tool_name] = result
                    results.append(result)
                except Exception as e:
                    rprint(f"[bold red][Executor] Erro na ferramenta {tool_name}:[/bold red] {str(e)}")
                    results.append(f"Error: Tool '{tool_name}' crashed -> {str(e)}")
            else:
                rprint(f"[bold red][Executor] Erro:[/bold red] Ferramenta '{tool_name}' não encontrada.")
                results.append(f"Error: Tool '{tool_name}' not found.")
        
        rprint("[bold green]--- Execução Finalizada ---[/bold green]\n")
        return results
