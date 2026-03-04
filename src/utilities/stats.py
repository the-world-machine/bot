import asyncio
import os
from datetime import datetime
from typing import NamedTuple

import psutil


class Stats(NamedTuple):
	cpu: float
	ram: float
	last_updated: datetime


stats = Stats(0.0, 0.0, datetime.now())


async def system_monitor_task():
	global stats
	process = psutil.Process(os.getpid())

	while True:
		stats = Stats(process.cpu_percent(interval=1), process.memory_percent(), datetime.now())
		await asyncio.sleep(5)


def get_stats():
	return stats
