from babel import Locale
from babel.dates import format_timedelta
from humanfriendly import format_timespan


import re
from datetime import timedelta
from typing import Literal


def amperjoin(items: list[str]):
	items = list(map(str, items))
	if len(items) == 0:
		return ""
	if len(items) == 1:
		return f"{items[0]}"
	if len(items) == 2:
		return " & ".join(items)
	return ", ".join(items[:-1]) + " & " + items[-1]


def english_ordinal_for(n: int | float):
	if isinstance(n, float):
		n = int(str(n).split('.')[1][0])

	if 10 <= int(n) % 100 <= 20:
		suffix = 'th'
	else:
		suffix = { 1: 'st', 2: 'nd', 3: 'rd'}.get(int(n) % 10, 'th')

	return suffix


def ftime(
	duration: timedelta | float,
	locale: str = "en",
	bold: bool = True,
	format: Literal['narrow', 'short', 'medium', 'long'] = "narrow",
	max_units: int = 69,
	minimum_unit: Literal["year", "month", "week", "day", "hour", "minute", "second"] = "second",
	**kwargs
) -> str:
	locale = Locale.parse(locale, sep="-").language

	if isinstance(duration, (int, float)):
		duration = timedelta(seconds=duration)

	formatted = format_timespan(duration, max_units=max_units).replace(" and", ",")

	unit_hierarchy = [ "year", "month", "week", "day", "hour", "minute", "second"]
	min_unit_index = unit_hierarchy.index(minimum_unit)

	def translate_unit(component: str) -> str:
		amount, unit = component.split(" ", 1)

		if not unit.endswith('s'):
			unit += "s"

		amount = float(amount)
		if unit == "years":
			unit = "weeks"
			amount *= 52.1429

		translated_component = format_timedelta(timedelta(**{ unit: amount}), locale=locale, format=format, **kwargs)
		return translated_component

	filtered_components = [
		part for part in formatted.split(", ")
		if unit_hierarchy.index(part.split(" ", 1)[1].rstrip('s')) <= min_unit_index
	]

	translated = ", ".join([translate_unit(part) for part in filtered_components])

	if bold:
		translated = re.sub(r'(\d+)', r'**\1**', translated)
	return translated


def fnum(num: float | int, locale: str = "en", ordinal: bool = False) -> str:
	if isinstance(num, float):
		fmtd = '{:,.3f}'.format(num)
	else:
		fmtd = '{:,}'.format(num)
	if locale in ("ru", "uk", "be", "kk", "ro", "sr", "bg"):
		fmtd = fmtd.replace(",", " ")

	if ordinal and isinstance(num, int) and locale not in ("ru", "uk", "be", "kk", "ro", "sr", "bg"):
		fmtd += english_ordinal_for(num)

	return fmtd