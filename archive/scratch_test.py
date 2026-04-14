import asyncio
import edge_tts
import sys
sys.stdout.reconfigure(encoding='utf-8')

async def amain():
    text = "哈囉大家好，這是一個測試。測試一下標點符號，能不能正確斷句！"
    c = edge_tts.Communicate(text, "zh-TW-YunJheNeural")
    sm = edge_tts.SubMaker()
    async for mk in c.stream():
        if mk['type'] != 'audio':
            print(mk)
    print(sm.get_srt())

if __name__ == "__main__":
    asyncio.run(amain())
