"""
Tool registry for the Friday agent.

``get_registered_tools()`` returns the complete list of tools available to
the LLM on every invocation — static core tools plus any dynamically
loaded skill runners and skill agent tools.
"""

from agent.tools.os_tools import (
    append_to_file,
    create_directory,
    delete_file,
    execute_bash_command,
    execute_in_directory,
    list_files,
    read_file,
    write_to_file,
)
from agent.tools.market_data import compare_stock_prices, get_stock_quote
from agent.tools.skill_agent import (
    create_skill_agent,
    list_skill_agents,
    load_skill_context,
    update_skill_agent,
)
from agent.tools.skill_library import (
    get_dynamic_skill_tools,
    save_to_skill_library,
    search_skill_library,
)
from agent.tools.web_search import web_search


def get_registered_tools() -> list:
    """Assemble and return the full tool list.

    Static tools (always available):
    - **Web**: ``web_search``
    - **Files**: ``list_files``, ``read_file``, ``write_to_file``,
      ``append_to_file``, ``create_directory``, ``delete_file``
    - **Shell**: ``execute_bash_command``, ``execute_in_directory``
    - **Skill library**: ``save_to_skill_library``, ``search_skill_library``
    - **Skill agents**: ``create_skill_agent``, ``load_skill_context``,
      ``list_skill_agents``, ``update_skill_agent``

    Dynamic tools (loaded from ``skills/index.json``):
    - ``skill_<name>`` — one per committed skill script.
    """
    static_tools = [
        # Web
        web_search,
        # Market data
        get_stock_quote,
        compare_stock_prices,
        # File operations
        list_files,
        read_file,
        write_to_file,
        append_to_file,
        create_directory,
        delete_file,
        # Shell execution
        execute_bash_command,
        execute_in_directory,
        # Skill library
        save_to_skill_library,
        search_skill_library,
        # Skill agents
        create_skill_agent,
        load_skill_context,
        list_skill_agents,
        update_skill_agent,
    ]
    return static_tools + get_dynamic_skill_tools()
