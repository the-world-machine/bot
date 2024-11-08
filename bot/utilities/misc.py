from io import BytesIO
from PIL import Image
import aiohttp

_yac: dict[str, Image.Image] = {}

async def get_image(url: str) -> Image.Image:
  if url in _yac:
    return Image.open(_yac[url])
  
  async with aiohttp.ClientSession() as session:
    async with session.get(url) as resp:
      if resp.status == 200:
        file = BytesIO(await resp.read())

        _yac[url] = file
        return Image.open(_yac[url])
      else:
        raise ValueError(f"{resp.status} Discord cdn shittig!!")