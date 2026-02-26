import sys
from typing import Literal

run: Literal["bot", "textboxweb"] = "bot"
if len(sys.argv) > 1:
	if sys.argv[1] not in ("bot", "textboxweb"):
		raise ValueError(f"Invalid project passed to run script (available: bot / textboxweb, passed: {run})")
	run = sys.argv[1]


match run:
	case "bot":
		import main
	case "textboxweb":
		from utilities.textbox.web.run import run_server

		run_server()
