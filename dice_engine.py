import re
import random

def roll_dice(expression: str):
    """
    Parses a dice expression (e.g., "1d20+5") and returns the result.
    
    Args:
        expression (str): The dice string (e.g., "2d6", "1d20+3", "d8-1").
        
    Returns:
        dict: {
            "total": int,
            "rolls": list[int],
            "expression": str,
            "detail": str
        }
    """
    # Clean string
    expr = expression.lower().replace(" ", "")
    
    # Regex for XdY[+|-]Z
    pattern = r"(\d*)d(\d+)([+-]\d+)?"
    match = re.search(pattern, expr)
    
    if not match:
        return {"error": f"Invalid format: {expression}. Use format like '1d20+5'."}
    
    # Parse Groups
    count_str = match.group(1)
    sides_str = match.group(2)
    mod_str = match.group(3)
    
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    mod = int(mod_str) if mod_str else 0
    
    # Limit for safety
    if count > 50: return {"error": "Too many dice!"}
    if sides > 1000: return {"error": "Too many sides!"}
    
    # Roll
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + mod
    
    # Format detail string
    sign = "+" if mod >= 0 else ""
    mod_text = f"{sign}{mod}" if mod_str else ""
    detail = f"{rolls}{mod_text}"
    
    return {
        "total": total,
        "rolls": rolls,
        "expression": str(expression),
        "detail": detail
    }

if __name__ == "__main__":
    # Test
    print(roll_dice("1d20+5"))
    print(roll_dice("2d6"))
