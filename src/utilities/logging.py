import logging
import time

class IgnoreFilter(logging.Filter):
	def __init__(self, ignored):
		super().__init__()
		self.ignored = ignored

	def filter(self, message):
		return not any(ignored_msg in message.getMessage() for ignored_msg in self.ignored)

ignored = [
	"❤ Gateway is sending a Heartbeat",
	"❤ Received heartbeat acknowledgement from gateway",
	"Sending data to websocket: {\"op\": 1, \"d\": 18}"
]
def createLogger(name):
	logger = logging.getLogger(name)
	logger.setLevel(logging.DEBUG)

	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

	for handler in [logging.FileHandler(f'logs/{time.strftime("%Y.%m.%d")}.log', mode="a", encoding='utf-8'), logging.StreamHandler()]:
		handler.setLevel(logging.DEBUG)
		handler.addFilter(IgnoreFilter(ignored))
		handler.setFormatter(formatter)
		logger.addHandler(handler)

	return logger
