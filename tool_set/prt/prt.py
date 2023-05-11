import os
import javalang
from line_parser import parse_stmt
import pickle
import random
import re
random.seed(666)
import sys


def get_split_count(record_list):
	count = 0
	for token in record_list:
		if token == "rank2fixsplit":
			count += 1
	return count


def find_if_statement(node, start_line):
	if node:
		if type(node) == list:
			for child in node:
				parsed_node = find_if_statement(child, start_line)
				if parsed_node:
					return parsed_node
		elif isinstance(node, javalang.tree.Node):
			if node.position and node.position[0] == start_line and type(node).__name__ == "IfStatement":
				return node
			for child in node.children:
				parsed_node = find_if_statement(child, start_line)
				if parsed_node:
					return parsed_node
	return None


def find_deepest_else_part(node):
	if node.else_statement:
		else_part = node.else_statement
		if type(else_part).__name__ == "IfStatement":
			result = find_deepest_else_part(else_part)
			if result:
				else_part = result
		return else_part
	else:
		return None


def beautify(method):
	method = method.replace(";", ";\n").replace("{", "{\n").replace("}", "\n}\n")
	return method


def change_for_mutate(origin_token, replaced_token, base_string, method_lines, anno_line_index, parse_type="normal"):
	candidates = []
	if parse_type == "normal":
		escape_token = re.escape(origin_token)
		escape_token = " " + escape_token + " "
		all_start_pos = [substr.start() for substr in re.finditer(escape_token, base_string)]
		all_start_pos = [factor + 1 for factor in all_start_pos]
		for each_start_pos in all_start_pos:
			each_end_pos = each_start_pos + len(origin_token)
			base_string = base_string[:each_start_pos] + replaced_token + base_string[each_end_pos:]
		try:
			tokens = javalang.tokenizer.tokenize(base_string)
			base_string = " ".join([token.value for token in tokens])
			candidates.append("\n".join(method_lines[:anno_line_index - 1]) + "\n" + base_string + "\n" +
							  "\n".join(method_lines[anno_line_index:]))
		except javalang.tokenizer.LexerError:
			pass
	else:
		for i in range(len(origin_token)):
			buggy_token = origin_token[i]
			escape_token = re.escape(buggy_token)
			escape_token = " " + escape_token + " "
			patch_token = replaced_token[i]
			all_start_pos = [substr.start() for substr in re.finditer(escape_token, base_string)]
			all_start_pos = [factor + 1 for factor in all_start_pos]
			# judge if in a bracket, because the type is argument
			all_start_pos = [factor for factor in all_start_pos if "(" in base_string[:factor + 1]]
			if all_start_pos:
				random_index = random.randint(0, len(all_start_pos) - 1)
				select_start_index = all_start_pos[random_index]
				select_end_index = select_start_index + len(buggy_token)
				already_delete_comma = False
				# delete corresponding commas for MutateMethodInv3
				if parse_type == "multi_delete":
					if select_end_index + 1 < len(base_string):
						if base_string[select_end_index + 1] == ",":
							select_end_index += 2  # delete the after ","
							already_delete_comma = True
					if not already_delete_comma and select_start_index - 2 >= 0:
						if base_string[select_start_index - 2] == ",":
							select_start_index -= 2  # delete the before ","
				base_string = base_string[:select_start_index] + patch_token + base_string[select_end_index:]
				# get standard form to correctly parse next token
				try:
					tokens = javalang.tokenizer.tokenize(base_string)
					base_string = " ".join([token.value for token in tokens])
				except javalang.tokenizer.LexerError:
					return None
			else:
				return None
		candidates.append("\n".join(method_lines[:anno_line_index - 1]) + "\n" + base_string + "\n" +
						  "\n".join(method_lines[anno_line_index:]))
	return candidates


def get_default_value(root):
	# constructor rather method
	if not root.types[0].methods:
		return "constructor"
	return_type = root.types[0].methods[0].return_type
	# for void
	if not return_type:
		return ""
	if isinstance(return_type, javalang.tree.BasicType):
		if return_type.name == "int" or return_type.name == "long" \
			or return_type.name == "short" or return_type.name == "byte":
			return "0"
		elif return_type.name == "double" or return_type.name == "float":
			return "0.0"
		elif return_type.name == "boolean":
			return "false"
		elif return_type.name == "char":
			return "\'\'"
	else:
		if return_type.name == "String":
			return "\"\""
		else:
			return "null"


def find_cast_expression(ast_node):
	if not ast_node:
		return None
	elif type(ast_node) == list:
		for child in ast_node:
			result = find_cast_expression(child)
			if result:
				return result
	elif isinstance(ast_node, javalang.tree.Node):
		if not isinstance(ast_node, javalang.tree.Cast):
			for child in ast_node.children:
				result = find_cast_expression(child)
				if result:
					return result
		else:
			if isinstance(ast_node.type, javalang.tree.BasicType):
				return ast_node.type.name
			elif isinstance(ast_node.type, javalang.tree.ReferenceType):
				if ast_node.type.arguments:
					gene_type = ast_node.type.arguments[0].pattern_type
					if gene_type == "?":
						return "{} <{}>".format(ast_node.type.name, gene_type)
					else:
						return "{} <? {} {}>".format(ast_node.type.name, gene_type, ast_node.type.arguments[0].type.name)
				else:
					return ast_node.type.name
			else:
				return None
	else:
		return None

def parse(record, method):
	patterns = ["InsertCastChecker", "InsertMissedStmt1", "InsertMissedStmt2", "InsertMissedStmt3", "InsertMissedStmt4",
		"MutateDataType1", "MutateDataType2", "InsertNullPointerChecker1", "InsertNullPointerChecker2",
		"InsertNullPointerChecker3", "InsertNullPointerChecker4", "InsertNullPointerChecker5", "InsertRangeChecker1",
		"InsertRangeChecker2", "MutateClassInstanceCreation", "MutateReturnStmt", "MutateConditionalExpr1",
		"MutateConditionalExpr2", "MutateConditionalExpr3", "MutateOperators1", "MutateOperators2",
		"MutateOperators3", "MutateVariable1", "MutateVariable2", "MutateMethodInvExpr1", "MutateMethodInvExpr2",
		"MutateMethodInvExpr3", "MutateMethodInvExpr4", "MutateLiteralExpr1", "MutateLiteralExpr2",
		"MutateIntegerDivisionOperation1", "MutateIntegerDivisionOperation2", "MutateIntegerDivisionOperation3",
		"MoveStmt", "RemoveBuggyStmt", "SingleLineMutator", "MultiLineMutator"]
	record = record.strip()
	if not record:
		return None
	record_list = record.split(" ")
	if record_list[0] not in patterns:
		return None
	pattern = record_list[0]
	split_count = get_split_count(record_list)
	method_lines = method.split("\n")

	# for mutate
	anno_line_index = -1
	for i, line in enumerate(method_lines):
		if line.strip().startswith("rank2fixstart"):
			anno_line_index = i + 1
			break
	try:
		tokens = javalang.tokenizer.tokenize(method)
		tokens = [token.value for token in tokens]
	except javalang.tokenizer.LexerError:
		return None
	start_index = tokens.index("rank2fixstart")
	end_index = tokens.index("rank2fixend")
	inner_tokens = " ".join(tokens[start_index: end_index + 1])

	stmt_list, anno_stmt = parse_stmt(method)
	if pattern != "SingleLineMutator" and pattern != "MultiLineMutator":
		if not anno_stmt:
			return None

	parsed_method_candidates = []
	if pattern == "InsertCastChecker":
		if split_count != 2:
			return None
		_, expr, cast_type = record.split("rank2fixsplit")
		expr = expr.strip()
		cast_type = cast_type.strip()
		'''
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"if ({} instanceof {})".format(expr, cast_type) + "{\n" + \
						"\n".join(method_lines[anno_stmt.start - 1: anno_stmt.end]) + \
						"\n}" + "else{\nthrow new IllegalArgumentException(\"Illegal argument\");\n}\n" + \
						"\n".join(method_lines[anno_stmt.end:])
		parsed_method_candidates.append(parsed_method)
		'''
		result = find_cast_expression(anno_stmt.origin_node)
		if result:
			parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
							"if ({} instanceof {})".format(expr, result) + "{\n" + \
							"\n".join(method_lines[anno_stmt.start - 1: anno_stmt.end]) + \
							"\n}" + "else{\nthrow new IllegalArgumentException(\"Illegal argument\");\n}\n" + \
							"\n".join(method_lines[anno_stmt.end:])
			parsed_method_candidates.append(parsed_method)

	elif pattern == "InsertNullPointerChecker1":
		if split_count != 1:
			return None
		_, expr = record.split("rank2fixsplit")
		expr = expr.strip()
		if expr == "null":
			return None
		anno_stmt_index = stmt_list.index(anno_stmt)
		nearest_stmt = stmt_list[anno_stmt_index]
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"if ({} != null)".format(expr) + "{\n" + \
						"\n".join(method_lines[anno_stmt.start - 1: nearest_stmt.end]) + "\n}\n" + \
						"\n".join(method_lines[nearest_stmt.end:])
		parsed_method_candidates.append(parsed_method)
		
	elif pattern == "InsertNullPointerChecker2":
		if split_count != 2:
			return None
		_, expr, _ = record.split("rank2fixsplit")
		expr = expr.strip()
		if expr == "null":
			return None
		method = method.replace(" rank2fixstart ", "").replace(" rank2fixend ", "")
		clazz_string = "public class Tmp { \n" + method + "\n}"
		tokens = javalang.tokenizer.tokenize(clazz_string)
		parser = javalang.parser.Parser(tokens)
		root = parser.parse()
		default_value = get_default_value(root)
		if default_value == "constructor":
			return None
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"if ({} == null) ".format(expr) + "return {};\n".format(default_value) + \
						"\n".join(method_lines[anno_stmt.start - 1:])
		parsed_method_candidates.append(parsed_method)

	elif pattern == "InsertNullPointerChecker3":
		if split_count != 2:
			return None
		_, expr, expr_1 = record.split("rank2fixsplit")
		expr = expr.strip()
		expr_1 = expr_1.strip()
		if expr == "null":
			return None
		if expr_1 != "\"STRING\"":
			parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
							"if ({} == null) ".format(expr) + "{} = {};\n".format(expr, expr_1) + \
							"\n".join(method_lines[anno_stmt.start - 1:])
		else:
			parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
							"if ({} == null) ".format(expr) + "{} = {};\n".format(expr, "\"\"") + \
							"\n".join(method_lines[anno_stmt.start - 1:])
		parsed_method_candidates.append(parsed_method)

	elif pattern == "InsertNullPointerChecker4":
		if split_count != 1:
			return None
		_, expr = record.split("rank2fixsplit")
		expr = expr.strip()
		if expr == "null":
			return None
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"if ({} == null) ".format(expr) + "continue;\n" + \
						"\n".join(method_lines[anno_stmt.start - 1:])
		parsed_method_candidates.append(parsed_method)

	elif pattern == "InsertNullPointerChecker5":
		if split_count != 1:
			return None
		_, expr = record.split("rank2fixsplit")
		expr = expr.strip()
		if expr == "null":
			return None
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"if ({} == null) ".format(expr) + "throw new IllegalArgumentException();\n" + \
						"\n".join(method_lines[anno_stmt.start - 1:])
		parsed_method_candidates.append(parsed_method)

	elif pattern == "InsertRangeChecker1":
		if split_count != 2:
			return None
		_, expr, index = record.split("rank2fixsplit")
		expr = expr.strip()
		index = index.strip()
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"if ({} < {}.length)".format(index, expr) + "{\n" + \
						"\n".join(method_lines[anno_stmt.start - 1: anno_stmt.end]) + "\n}\n" + \
						"\n".join(method_lines[anno_stmt.end:])
		parsed_method_candidates.append(parsed_method)

	elif pattern == "InsertRangeChecker2":
		if split_count != 2:
			return None
		_, expr, index = record.split("rank2fixsplit")
		expr = expr.strip()
		index = index.strip()
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"if ({} < {}.size())".format(index, expr) + "{\n" + \
						"\n".join(method_lines[anno_stmt.start - 1: anno_stmt.end]) + "\n}\n" + \
						"\n".join(method_lines[anno_stmt.end:])
		parsed_method_candidates.append(parsed_method)

	elif pattern == "InsertMissedStmt1":
		if split_count != 1:
			return None
		_, stmt = record.split("rank2fixsplit")
		stmt = stmt.strip()
		if stmt.startswith("System . exit"):
			return None
		# solve_1: insert before the anno stmt
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						stmt + "\n" + "\n".join(method_lines[anno_stmt.start - 1:])
		parsed_method_candidates.append(parsed_method)
		'''
		# solve_2: insert after the anno stmt
		parsed_method = "\n".join(method_lines[:anno_stmt.end]) + "\n" + \
						stmt + "\n" + "\n".join(method_lines[anno_stmt.end:])
		parsed_method_candidates.append(parsed_method)
		# solve_3: delete the anno stmt and then insert
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						stmt + "\n" + "\n".join(method_lines[anno_stmt.end:])
		parsed_method_candidates.append(parsed_method)
		'''
	elif pattern == "InsertMissedStmt2":
		if split_count != 1:
			return None
		_, return_value = record.split("rank2fixsplit")
		return_value = return_value.strip()
		if "rank2fixempty" in return_value:
			return_value = ""
		# solve_1: insert before the anno stmt
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"return {};\n".format(return_value) + "\n".join(method_lines[anno_stmt.start - 1:])
		parsed_method_candidates.append(parsed_method)
		'''
		# solve_2: insert after the anno stmt
		parsed_method = "\n".join(method_lines[:anno_stmt.end]) + "\n" + \
						"return {};\n".format(return_value) + "\n".join(method_lines[anno_stmt.end:])
		parsed_method_candidates.append(parsed_method)
		'''
	elif pattern == "InsertMissedStmt3":
		return None
		'''
		if split_count != 0:
			return None
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"try {\n" + "\n".join(method_lines[anno_stmt.start - 1: anno_stmt.end]) + \
						"\n}catch (Exception e){;}\n" + "\n".join(method_lines[anno_stmt.end:])
		parsed_method_candidates.append(parsed_method)
		'''

	elif pattern == "InsertMissedStmt4":
		if split_count != 1:
			return None
		_, expr = record.split("rank2fixsplit")
		expr = expr.strip()
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"if ({})".format(expr) + "{\n" + \
						"\n".join(method_lines[anno_stmt.start - 1: anno_stmt.end]) + "\n}\n" + \
						"\n".join(method_lines[anno_stmt.end:])
		parsed_method_candidates.append(parsed_method)

	elif pattern == "RemoveBuggyStmt":
		if split_count != 0:
			return None
		parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
						"\n".join(method_lines[anno_stmt.end:])
		parsed_method_candidates.append(parsed_method)
		
		if anno_stmt.node_type == "IfStatement":
			method = method.replace(" rank2fixstart ", "").replace(" rank2fixend ", "")
			clazz_string = "public class Tmp { \n" + method + "\n}"
			tokens = javalang.tokenizer.tokenize(clazz_string)
			parser = javalang.parser.Parser(tokens)
			root = parser.parse()
			ifstmt_node = find_if_statement(root, anno_stmt.start + 1)
			method_lines = method.split("\n")
			filter_space_line = re.sub(r"\s+", " ", method_lines[anno_stmt.start - 1].strip())
			if filter_space_line.startswith("else if"):
				if ifstmt_node.else_statement:
					else_start_line = ifstmt_node.else_statement.position[0] - 1
					parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
									"\n".join(method_lines[else_start_line - 1:])
					parsed_method_candidates.append(parsed_method)
			'''
			elif filter_space_line.startswith("if"):
				deepest_else_node = find_deepest_else_part(ifstmt_node)
				if deepest_else_node:
					else_start_line = deepest_else_node.position[0] - 1
					parsed_method = "\n".join(method_lines[:anno_stmt.start - 1]) + "\n" + \
									"\n".join(method_lines[else_start_line:anno_stmt.end - 1]) + "\n" + \
									"\n".join(method_lines[anno_stmt.end:])
					parsed_method_candidates.append(parsed_method)
			'''
		# delete the whole method
		parsed_method_candidates.append("")

	elif pattern == "MoveStmt":
		if split_count != 1:
			return None
		_, move_step = record.split("rank2fixsplit")
		move_step = move_step.strip()
		tmp_list = move_step.split(" ")
		if len(tmp_list) == 1 and str.isdigit(tmp_list[0]) and "." not in tmp_list[0]:
			move_step = int(tmp_list[0])
		elif len(tmp_list) == 2 and tmp_list[0] == "-" and str.isdigit(tmp_list[1]) and "." not in tmp_list[1]:
			move_step = -int(tmp_list[1])
		else:
			return None
		if abs(move_step) > 3:
			return None
		real_start = anno_stmt.start + move_step
		anno_part = method_lines[anno_stmt.start - 1: anno_stmt.end]
		other_part = method_lines[:anno_stmt.start - 1] + method_lines[anno_stmt.end:]
		if real_start <= 1 or real_start > len(other_part):
			return None
		parsed_method = "\n".join(other_part[:real_start-1]) + "\n" + "\n".join(anno_part) + "\n" + "\n".join(other_part[real_start-1:])
		parsed_method_candidates.append(parsed_method)

	elif pattern == "MutateConditionalExpr1":
		if split_count != 2:
			return None
		_, cond_expr1, cond_expr2 = record.split("rank2fixsplit")
		cond_expr1 = cond_expr1.strip()
		cond_expr2 = cond_expr2.strip()
		parsed_method = change_for_mutate(cond_expr1, cond_expr2, inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateConditionalExpr2":
		if split_count != 2:
			return None
		_, op, cond_expr = record.split("rank2fixsplit")
		op = op.strip()
		cond_expr = cond_expr.strip()
		op_and_expr = "{} {}".format(op, cond_expr)
		parsed_method = change_for_mutate(op_and_expr, "", inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateConditionalExpr3":
		if split_count != 3:
			return None
		_, cond_expr1, op, cond_expr2 = record.split("rank2fixsplit")
		cond_expr1 = cond_expr1.strip()
		op = op.strip()
		cond_expr2 = cond_expr2.strip()
		expr1_op_expr2 = "{} {} {}".format(cond_expr1, op, cond_expr2)
		parsed_method = change_for_mutate(cond_expr1, expr1_op_expr2, inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateDataType1":
		if split_count != 2:
			return None
		_, type1, type2 = record.split("rank2fixsplit")
		type1 = type1.strip()
		type2 = type2.strip()
		parsed_method = change_for_mutate(type1, type2, inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateDataType2":
		if split_count != 2:
			return None
		_, type1, type2 = record.split("rank2fixsplit")
		type1 = type1.strip()
		type2 = type2.strip()
		parsed_method = change_for_mutate(type1, type2, inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateIntegerDivisionOperation1":
		if split_count != 1:
			return None
		_, divisor = record.split("rank2fixsplit")
		divisor = divisor.strip()
		parsed_method = change_for_mutate(divisor, "(double) {}".format(divisor), inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateIntegerDivisionOperation2":
		if split_count != 1:
			return None
		_, dividend = record.split("rank2fixsplit")
		dividend = dividend.strip()
		parsed_method = change_for_mutate(dividend, "(double) {}".format(dividend), inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateIntegerDivisionOperation3":
		if split_count != 2:
			return None
		_, dividend, divisor = record.split("rank2fixsplit")
		dividend = dividend.strip()
		divisor = divisor.strip()
		parsed_method = change_for_mutate("{} / {}".format(dividend, divisor), "(1.0 / {}) * {}".format(divisor, dividend), inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateLiteralExpr1" or pattern == "MutateLiteralExpr2":
		if split_count != 2:
			return None
		_, literal1, literal2_or_expr = record.split("rank2fixsplit")
		literal1 = literal1.strip()
		literal2_or_expr = literal2_or_expr.strip()
		if pattern == "MutateLiteralExpr1":
			if not (literal2_or_expr.isdigit() or literal2_or_expr == "true" or literal2_or_expr == "false" or literal2_or_expr == "null" \
				or literal2_or_expr.startswith("\'") or literal2_or_expr.startswith("\"")):
				return None
		parsed_method = change_for_mutate(literal1, literal2_or_expr, inner_tokens, method_lines, anno_line_index)
		if parsed_method:
			parsed_method_candidates += parsed_method
		if literal1.isdigit():
			if "." not in literal1:
				literal2_or_expr = str(float(int(literal1)))
				parsed_method = change_for_mutate(literal1, literal2_or_expr, inner_tokens, method_lines, anno_line_index)
				if parsed_method:
					parsed_method_candidates += parsed_method

	elif pattern == "MutateOperators1":
		if split_count != 2:
			return None
		_, op1, op2 = record.split("rank2fixsplit")
		op1 = op1.strip()
		op2 = op2.strip()
		parsed_method = change_for_mutate(op1, op2, inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateOperators2":
		if split_count != 2:
			return None
		_, buggy_infix, patch_infix = record.split("rank2fixsplit")
		buggy_infix = buggy_infix.strip()
		patch_infix = patch_infix.strip()
		parsed_method = change_for_mutate(buggy_infix, patch_infix, inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateOperators3":
		if split_count != 2:
			return None
		_, expr, expr_type = record.split("rank2fixsplit")
		expr = expr.strip()
		expr_type = expr_type.strip()
		parsed_method = change_for_mutate("{} instanceof {}".format(expr, expr_type), "{} != null".format(expr), inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateReturnStmt":
		if split_count != 2:
			return None
		_, expr1, expr2 = record.split("rank2fixsplit")
		expr1 = expr1.strip()
		expr2 = expr2.strip()
		parsed_method = change_for_mutate(expr1, expr2, inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateVariable1" or pattern == "MutateVariable2":
		if split_count != 2:
			return None
		_, var1, var2_or_expr = record.split("rank2fixsplit")
		var1 = var1.strip()
		var2_or_expr = var2_or_expr.strip()
		parsed_method = change_for_mutate(var1, var2_or_expr, inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateMethodInvExpr1":
		if split_count != 2:
			return None
		_, method_name1, method_name2 = record.split("rank2fixsplit")
		method_name1 = method_name1.strip()
		method_name2 = method_name2.strip()
		parsed_method = change_for_mutate(method_name1, method_name2, inner_tokens, method_lines, anno_line_index)
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateMethodInvExpr2":
		if split_count != 2:
			return None
		_, buggy_changed_args, patch_changed_args = record.split("rank2fixsplit")
		buggy_args = buggy_changed_args.strip().split("rank2fixdelimiter")
		buggy_args = [factor.strip() for factor in buggy_args]
		patch_args = patch_changed_args.strip().split("rank2fixdelimiter")
		patch_args = [factor.strip() for factor in patch_args]
		if not len(buggy_args) == len(patch_args):
			return None
		parsed_method = change_for_mutate(buggy_args, patch_args, inner_tokens, method_lines, anno_line_index, "multi_replace")
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateMethodInvExpr3":
		if split_count != 1:
			return None
		_, deleted_args = record.split("rank2fixsplit")
		deleted_args = deleted_args.strip().split("rank2fixdelimiter")
		deleted_args = [factor.strip() for factor in deleted_args]
		fake_args = [""] * len(deleted_args)
		parsed_method = change_for_mutate(deleted_args, fake_args, inner_tokens, method_lines, anno_line_index, "multi_delete")
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	elif pattern == "MutateMethodInvExpr4":
		if split_count != 3:
			return None
		_, corres_args, inter_inserted_args, follow_inserted_args = record.split("rank2fixsplit")
		corres_args = corres_args.strip()
		corres_args = [] if not corres_args else [factor.strip() for factor in corres_args.split("rank2fixdelimiter")]
		inter_inserted_args = inter_inserted_args.strip()
		inter_inserted_args = [] if not inter_inserted_args else [factor.strip() for factor in inter_inserted_args.split("rank2fixdelimiter")]
		follow_inserted_args = follow_inserted_args.strip()
		follow_inserted_args = [] if not follow_inserted_args else [factor.strip() for factor in follow_inserted_args.split("rank2fixdelimiter")]

		if len(inter_inserted_args) + len(follow_inserted_args) == 0:
			return None
		if not len(corres_args) == len(inter_inserted_args) + len(follow_inserted_args):
			return None
		match = {}
		for index in range(len(inter_inserted_args)):
			if corres_args[index] not in match:
				match[corres_args[index]] = {}
				match[corres_args[index]]["before"] = []
				match[corres_args[index]]["after"] = []
			match[corres_args[index]]["before"].append(inter_inserted_args[index])
		for index in range(len(follow_inserted_args)):
			if corres_args[len(inter_inserted_args) + index] not in match:
				match[corres_args[len(inter_inserted_args) + index]] = {}
				match[corres_args[len(inter_inserted_args) + index]]["before"] = []
				match[corres_args[len(inter_inserted_args) + index]]["after"] = []
			match[corres_args[len(inter_inserted_args) + index]]["after"].append(follow_inserted_args[index])
		before = []
		after = []
		for factor in match:
			if factor == "rank2fixargempty":
				before.append("( )")
				after.append("( {} )".format(",".join(match[factor]["after"])))
			else:
				before.append(factor)
				if match[factor]["before"] and match[factor]["after"]:
					after.append("{},{},{}".format(",".join(match[factor]["before"]), factor, ",".join(match[factor]["after"])))
				elif match[factor]["before"]:
					after.append("{},{}".format(",".join(match[factor]["before"]), factor))
				elif match[factor]["after"]:
					after.append("{},{}".format(factor, ",".join(match[factor]["after"])))
		parsed_method = change_for_mutate(before, after, inner_tokens, method_lines, anno_line_index, "multi_insert")
		if not parsed_method:
			return None
		parsed_method_candidates += parsed_method

	# no one
	elif pattern == "MutateClassInstanceCreation":
		return None

	elif pattern == "SingleLineMutator":
		if split_count != 1:
			return None
		_, replace_line = record.split("rank2fixsplit")
		if "System . exit" in replace_line:
			return None
		parsed_method = "\n".join(method_lines[:anno_line_index - 1] + [replace_line] + method_lines[anno_line_index:])
		if not parsed_method:
			return None
		parsed_method_candidates.append(parsed_method)

	return parsed_method_candidates


if __name__ == "__main__":
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]
	BEAM = int(sys.argv[4].strip())

	parsed_data_dir = "../../parsed_data/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version)
	pred_path = os.path.join(parsed_data_dir, "patch_irs.txt")
	src_path = os.path.join(parsed_data_dir, "data_no_empty/")
	out_dir = os.path.join(parsed_data_dir, "result/")
	if not os.path.exists(out_dir):
		os.makedirs(out_dir)
	out_path = os.path.join(out_dir, "patches_with_unk.pkl")

	with open(pred_path, "r") as file:
		pred = file.readlines()
	sample_count = len(os.listdir(src_path))
	assert sample_count * BEAM == len(pred)

	results = []
	for i in range(sample_count):
		print(i)
		with open(os.path.join(src_path, "{}.txt".format(i + 1)), "r") as file:
			method = file.read()
		current_pred = pred[i * BEAM: (i + 1) * BEAM]
		for record in current_pred:
			parsed_method_candidates = parse(record, method)
			if not parsed_method_candidates:
				results.append([])
			else:
				parsed_method_candidates = [factor.replace("rank2fixstart", "").replace("rank2fixend", "").replace("< unk >", "<unk>") for factor in parsed_method_candidates]
				results.append(parsed_method_candidates)
	with open(out_path, "wb") as file:
		pickle.dump(results, file)
