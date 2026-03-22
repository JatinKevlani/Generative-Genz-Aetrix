import asyncio
import os
from llm import query_historical_traffic, generate_chat_reply

async def main():
    print("--- Testing query_historical_traffic tool ---")
    try:
        res = query_historical_traffic.invoke({"road_name": "SG Highway"})
        print(res)
    except Exception as e:
        print(f"Tool error: {e}")
        
    print("\n--- Testing generate_chat_reply (without API key) ---")
    try:
        reply = await generate_chat_reply("What is the historical average speed on SG Highway?", "No sensors", "Normal")
        print(f"Reply: {reply}")
    except Exception as e:
        print(f"Chat error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
