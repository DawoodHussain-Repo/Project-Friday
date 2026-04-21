from agent.tools.mcp_client import mcp_call
from agent.tools.os_tools import execute_bash_command, list_files, read_file, write_to_file
from agent.tools.skill_library import (
    get_dynamic_skill_tools,
    save_to_skill_library,
    search_skill_library,
)
from agent.tools.web_search import web_search


def get_registered_tools() -> list:
    static_tools = [
        web_search,
        list_files,
        read_file,
        write_to_file,
        execute_bash_command,
        save_to_skill_library,
        search_skill_library,
        mcp_call,
    ]
    return static_tools + get_dynamic_skill_tools()
