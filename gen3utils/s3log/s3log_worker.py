import asyncio
import importlib
import re
import struct
import sys
from json import JSONDecoder, JSONDecodeError

NOT_WHITESPACE = re.compile(r"[^\s]")


async def stream_json(
    stdin, buf_size=65536, max_json=65536 * 16, decoder=JSONDecoder()
):
    buf = ""
    ex = None
    pending = True
    while pending:
        chunk = await stdin.read(buf_size)
        if chunk:
            buf += chunk.decode()
        else:
            pending = False
        pos = 0
        buf_len = len(buf)
        while pos < buf_len:
            match = NOT_WHITESPACE.search(buf, pos)
            if not match:
                break
            pos = match.start()
            if buf[pos] == "\x00":
                return
            start = pos
            try:
                obj, pos = decoder.raw_decode(buf, pos)
            except JSONDecodeError as e:
                if (not pending or len(buf) > max_json - buf_size) and (
                    ex is None or ex.pos == e.pos
                ):
                    pos = e.pos + 1
                    ex = None
                else:
                    print(
                        f"Cannot get JSON from chunk: {e}. Chunk:\n{buf}",
                        file=sys.stderr,
                    )
                    ex = e
                    break
            else:
                ex = None
                yield obj, buf[start:pos]
        buf = buf[pos:]
        if ex is not None:
            raise ex
    raise EOFError()


async def worker(loop, handle_row):
    stdin = asyncio.StreamReader()
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(stdin), sys.stdin)
    try:
        while True:
            lines = 0
            size = 0
            async for row, line in stream_json(stdin):
                lines += 1
                size += len(line)
                output = handle_row(row, line)
                if output:
                    print(output, file=sys.stderr)
            sys.stdout.buffer.write(struct.pack("QQ", lines, size))
            sys.stdout.flush()
    except EOFError:
        pass


def worker_main():
    script_module = sys.argv[1]
    handle_row = getattr(importlib.import_module(script_module), "handle_row")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker(loop, handle_row))


if __name__ == "__main__":
    worker_main()
