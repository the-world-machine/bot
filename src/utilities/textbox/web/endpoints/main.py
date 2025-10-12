from aiohttp import web
async def main_route(request: web.Request):
	return web.FileResponse('src/utilities/textbox/web/static/paiges/main.html')

def process(app: web.Application):
	app.router.add_get('/', main_route)