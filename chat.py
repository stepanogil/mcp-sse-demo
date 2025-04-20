import nest_asyncio
import json
import os
from openai import AsyncOpenAI
from mcp_clients.zapier_mcp_client import GmailMCPClient
from dotenv import load_dotenv

load_dotenv()

# load credentials from .env file
API_KEY = os.getenv("OPENAI_API_KEY") # 'sk-proj-...'
ZAPIER_URL = os.getenv("ZAPIER_URL") # 'https://actions.zapier.com/mcp/you-secret-key/sse'

client = AsyncOpenAI(api_key=API_KEY)

# allows async functions to run in jupyter notebook
nest_asyncio.apply()

# initialize the Gmail MCP client
gmail_mcp_client = GmailMCPClient()

# chat function
async def chat(user_input):
    """
    Processes user input through a two-step LLM interaction with tool integration.

    This function performs the following steps:
    1. Connects to Gmail MCP server and retrieves available tools
    2. Makes initial LLM call to determine which tool to use
    3. Executes the selected tool with provided arguments
    4. Makes second LLM call to generate final response based on tool output

    Args:
        user_input (str): The input message from the user to be processed

    Returns:
        str: The final response message from the LLM

    Raises:
        None
    """

    # get tools from Zapier server
    await gmail_mcp_client.connect_to_server(ZAPIER_URL)
    tools = await gmail_mcp_client.get_tools()    

    # 1st LLM call to determine which tool to use
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_input}],
        tools=tools
    )

    # if LLM decides to use a tool
    if response.choices[0].message.tool_calls:        
        tool_name = response.choices[0].message.tool_calls[0].function.name
        tool_args = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        print(f"Tool Used: {tool_name}, Arguments: {tool_args}")

        # execute the tool called by the LLM
        tool_response = await gmail_mcp_client.session.call_tool(tool_name, tool_args)
        tool_response_text = tool_response.content[0].text    

        # 2nd LLM call to determine final response
        res = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": user_input},
                {"role": "function", "name": tool_name, "content": tool_response_text},
            ]        
        )

        response = res.choices[0].message.content
        
    # if LLM decides not to use a tool
    else:
        response = response.choices[0].message.content

    # disconnect from the server
    await gmail_mcp_client.disconnect()
    
    return response    


