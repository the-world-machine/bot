class CommandParseError(ValueError):
	def __init__(self, message, position=None, command=None):
		super().__init__(message)
		self.position = position
		self.command = command
	def __str__(self):
		base = super().__str__()
		if self.position is not None:
			base += f" (position: {self.position})"
		if self.command is not None:
			base += f" (command: '{self.command}')"
		return base

def parse_textbox_text(input_str):
	tokens = []
	pos = 0
	length = len(input_str)

	while pos < length:
		if input_str[pos] == '\\':
			if pos + 1 < length and input_str[pos + 1] == '\\':
				if tokens and isinstance(tokens[-1], str):
					tokens[-1] += '\\'
				else:
					tokens.append('\\')
				pos += 2
				continue

			if pos + 1 < length and input_str[pos + 1] in { 'c', 'u', 'f', 'd', '@', 'n'}:
				cmd_char = input_str[pos + 1]
				command = { 'command': cmd_char, 'args': ''}
				args_start = pos + 2

				if args_start < length and input_str[args_start] == '[':
					bracket_pos = args_start
					bracket_depth = 1
					scan_pos = args_start + 1

					while scan_pos < length and bracket_depth > 0:
						if input_str[scan_pos] == '[':
							bracket_depth += 1
						elif input_str[scan_pos] == ']':
							bracket_depth -= 1
							if bracket_depth == 0:
								command['args'] = input_str[args_start + 1:scan_pos]
								pos = scan_pos + 1
								break
						scan_pos += 1

					if bracket_depth > 0:
						raise CommandParseError("Unclosed bracket", position=bracket_pos, command=f"\\{cmd_char}")

					tokens.append(command)
					continue
				else:
					tokens.append(command)
					pos += 2
					continue

			# lone backslash
			if tokens and isinstance(tokens[-1], str):
				tokens[-1] += '\\'
			else:
				tokens.append('\\')
			pos += 1
			continue

		next_cmd = input_str.find('\\', pos)
		if next_cmd == -1:
			text = input_str[pos:]
			pos = length
		else:
			text = input_str[pos:next_cmd]
			pos = next_cmd

		if text:
			tokens.append(text)

	merged = []
	for token in tokens:
		if merged and isinstance(token, str) and isinstance(merged[-1], str):
			merged[-1] += token
		else:
			merged.append(token)

	return merged


# text = "\\@[The World Machine:Normal]Hi!!!...\\n Oh,\\@[The World Machine:Eyes Closed] it's you."
# print(parse_textbox_text(text))
