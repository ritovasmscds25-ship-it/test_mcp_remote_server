from fastmcp import FastMCP
import random
import json

mcp = FastMCP("Simple Calculator Server")

@mcp.tool
def add(a: float, b: float) -> float:
    """Add two numbers together.
    
    Args:
        a (float): The first number.
        b (float): The second number.
    
    Returns:
        float: The sum of the two numbers.
    """
    return a + b

@mcp.tool
def random_number(min_value: int, max_value: int) -> int:
    """Generate a random number between min_value and max_value.
    
    Args:
        min_value (int): The minimum value (inclusive).
        max_value (int): The maximum value (inclusive).
    
    Returns:
        int: A random integer between min_value and max_value.
    """
    return random.randint(min_value, max_value)

@mcp.resource("info://server")
def server_info() -> str:
    """Get information about the server."""
    info  = {
        "name": "Simple Calculator Server",
        "version": "1.0.0",
        "description": "A simple server that provides basic calculator functions and random number generation.",
        "tools": ["add", "random_number"],
        "author": "Ritovas"
    }
    return json.dumps(info, indent=2)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)