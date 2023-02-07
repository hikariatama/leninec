import asyncio

import websockets


async def main():
    CODE = """add a 1
push a
push 5"""
    async with websockets.connect("ws://localhost:1111/ws") as wss:
        await wss.send("@delay 1")
        await wss.send(CODE)
        while True:
            data = await wss.recv()
            print(data)
            if data == "@f":
                break


if __name__ == "__main__":
    asyncio.run(main())
