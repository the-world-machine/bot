import os
import sys
import asyncio
import base64
import io
import time
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from aiohttp import web

from utilities.textbox.mediagen import Frame, render_textbox_frames, SupportedFiletypes
from utilities.textbox.states import State
from utilities.config import get_config

PORT = get_config("textbox.web.port", typecheck=int)
FILE_SIZE_LIMIT_BYTES = 20 * 1024 * 1024

static_files_path = Path(__file__).parent / "static"
routes = web.RouteTableDef()


@routes.get('/')
async def handle_index(request: web.Request):
	return web.FileResponse(static_files_path / 'index.html')


@routes.post('/generate')
async def handle_generate(request: web.Request):
	try:
		start_time = time.perf_counter()

		state_parse = State.from_string(await request.text(), owner=0)
		state, _, frame_index = state_parse
		image_buffer: io.BytesIO = await render_textbox_frames(
		    frames=state.frames,
		    quality=state.options.quality,
		    filetype=state.options.filetype,
		    frame_index=int(frame_index) if frame_index is not None else None
		)

		file_size = image_buffer.tell()
		if file_size > FILE_SIZE_LIMIT_BYTES:
			error_message = (
			    f"Generated file is too large ({file_size / 1024 / 1024:.2f} MB). "
			    f"Limit is {FILE_SIZE_LIMIT_BYTES / 1024 / 1024} MB."
			)
			return web.json_response({ 'error': error_message}, status=413)

		image_bytes = image_buffer.getvalue()
		base64_encoded_data = base64.b64encode(image_bytes).decode('utf-8')

		mime_type = f'image/{state.options.filetype.lower()}'
		if state.options.filetype == 'APNG':
			mime_type = 'image/apng'

		data_uri = f'data:{mime_type};base64,{base64_encoded_data}'

		end_time = time.perf_counter()
		duration_ms = (end_time - start_time) * 1000

		return web.json_response({ 'output_blob': data_uri, 'took': duration_ms})

	except Exception as e:
		print(f"Error during image generation: {e}")
		import traceback
		traceback.print_exc()
		return web.json_response({ 'error': str(e)}, status=500)


async def main():
	app = web.Application()
	app.add_routes(routes)
	app.router.add_static('/static/', path=static_files_path, name='static')

	if os.environ.get("AIOHTTP_RELOADER") != "1":
		print(f"🚀 Starting textbox preview server at http://localhost:{PORT}")

	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, None, PORT)
	await site.start()

	await asyncio.Event().wait()


if __name__ == "__main__":
	asyncio.run(main())
