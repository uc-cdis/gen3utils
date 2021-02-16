import aiobotocore
import asyncio
import os
import struct
import sys


def _unitize(value):
    unit = ["", "K", "M", "G", "T"]
    while value > 100 and unit:
        value /= 1024
        unit.pop(0)
    return value, unit[0]


def _speed(sub):
    value = (sub[-1][0] - sub[0][0]) / (sub[-1][1] - sub[0][1])
    value, unit = _unitize(value)
    return f"{value:.1f}{unit}B/s"


class S3Log:
    def __init__(
        self,
        bucket,
        prefix,
        script,
        region,
        access_key_id,
        secret_access_key,
        concurrency,
        progress,
    ):
        self._bucket = bucket
        self._prefix = prefix
        self._script = script
        self._aws_region = region
        self._aws_access_key_id = access_key_id
        self._aws_secret_access_key = secret_access_key
        self._concurrency = concurrency
        self._show_progress = progress

        self._loop = asyncio.get_event_loop()
        self._total_lines = 0
        self._total_received = 0
        self._total_processed = 0
        self._size_queue = []
        self._q = asyncio.Queue()
        self._tasks_queue = asyncio.Queue()

        print(
            f"Processing logs from {self._bucket}/{self._prefix} in {self._aws_region}",
            file=sys.stderr,
        )
        print(f"Concurrency: {self._concurrency}", file=sys.stderr)
        print(f"Show progress: {self._show_progress}", file=sys.stderr)

    async def _wait(self):
        while True:
            task = await self._tasks_queue.get()
            if not task:
                break
            await task

    async def feed(self, client, key, proc):
        response = await client.get_object(Bucket=self._bucket, Key=key)
        # this will ensure the connection is correctly re-used/closed
        async with response["Body"] as stream:
            size = 0
            while True:
                chunk = await stream.readany()
                if not chunk:
                    break
                proc.stdin.write(chunk)
                len_chunk = len(chunk)
                size += len_chunk
                self._total_received += len_chunk
                if size > 65536:
                    size = 0
                    await proc.stdin.drain()
            proc.stdin.write(b"\x00")
            await proc.stdin.drain()
            result = await proc.stdout.read(16)
            await self._q.put(proc)
            lines, size = struct.unpack("QQ", result)
            self._total_lines += lines
            self._total_processed += size

    async def _status(self):
        start = [(0, self._loop.time())]
        self._size_queue.extend(start)
        while True:
            await asyncio.sleep(1)
            self._size_queue.append((self._total_received, self._loop.time()))
            if len(self._size_queue) > 60:
                self._size_queue.pop(0)
            print(
                f"MA5: {_speed(self._size_queue[-5:])}\t",
                f"MA20: {_speed(self._size_queue[-20:])}\t",
                f"MA60: {_speed(self._size_queue)}\t",
                f"AVG: {_speed(start + self._size_queue[-1:])}\t",
                f"JSON: {self._total_processed / self._total_lines if self._total_lines else 0:,.0f}B",
                "Size: {:.1f}{}B".format(*_unitize(self._total_processed)),
                file=sys.stderr,
            )

    async def _run(self):
        for i in range(self._concurrency):
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "s3log_worker.py"
                ),
                self._script,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=sys.stdout,
            )
            await self._q.put(proc)

        session = aiobotocore.get_session(loop=self._loop)
        async with session.create_client(
            "s3",
            region_name=self._aws_region,
            aws_secret_access_key=self._aws_secret_access_key,
            aws_access_key_id=self._aws_access_key_id,
        ) as client:
            if self._show_progress:
                self._loop.create_task(self._status())
            waiter = self._loop.create_task(self._wait())
            # # list s3 objects using paginator
            paginator = client.get_paginator("list_objects")
            async for result in paginator.paginate(
                Bucket=self._bucket, Prefix=self._prefix
            ):
                for c in result.get("Contents", []):
                    key = c["Key"]
                    print(f"Processing key: {key}", file=sys.stderr)
                    proc = await self._q.get()
                    await self._tasks_queue.put(
                        self._loop.create_task(self.feed(client, key, proc))
                    )
            await self._tasks_queue.put(None)
            await waiter

    def run(self):
        self._loop.run_until_complete(self._run())
