import base64
import io
import time

from aiohttp import web

from utilities.config import get_config
from utilities.misc import io_buffer_bettell
from utilities.textbox.mediagen import render_textbox_frames
from utilities.textbox.states import State


async def generate_route(request: web.Request):
	try:
		start_time = time.perf_counter()

		state_parse = State.from_string(await request.text(), owner=0)
		state, _, frame_index = state_parse
		image_buffer: io.BytesIO = await render_textbox_frames(
			frames=state.frames,
			quality=state.options.quality,
			filetype=state.options.filetype,
			frame_index=int(frame_index) if frame_index is not None else None,
			loops=state.options.loops,
		)

		file_size = io_buffer_bettell(image_buffer)
		if file_size > get_config("textbox.limits.filesize", typecheck=int):
			error_message = (
				f"Generated file is too large ({file_size / 1024 / 1024:.2f} MB). "
				f"Limit is {get_config('textbox.limits.filesize', typecheck=int) / 1024 / 1024} MB."
			)
			return web.json_response({"error": error_message}, status=413)

		image_bytes = image_buffer.getvalue()
		base64_encoded_data = base64.b64encode(image_bytes).decode("utf-8")

		mime_type = f"image/{state.options.filetype.lower()}"
		if state.options.filetype == "APNG":
			mime_type = "image/apng"

		data_uri = f"data:{mime_type};base64,{base64_encoded_data}"

		end_time = time.perf_counter()
		duration_ms = (end_time - start_time) * 1000

		return web.json_response({"output_blob": data_uri, "took": duration_ms})

	except Exception as e:
		print(f"Error during image generation: {e}")
		import traceback

		traceback.print_exc()
		return web.json_response({"error": str(e)}, status=500)


def process(app: web.Application):
	app.router.add_post("/generate", generate_route)
