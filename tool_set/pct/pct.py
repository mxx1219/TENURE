import os
import pickle
import sys
import difflib
import javalang
from node_parser import get_expr, parse_specific_node


def check_method_syntax_correct(method):
	fake_clazz = "public class Tmp {\n" + method + "\n}"
	try:
		tokens = javalang.tokenizer.tokenize(fake_clazz)
		parser = javalang.parse.Parser(tokens)
		root = parser.parse()
		return True
	except:
		return False


def check_type_in_import(clazz, type_under_judge, global_info, jdk_info):
	in_jdk = False
	if type_under_judge not in global_info:
		in_jdk = True
		if type_under_judge not in jdk_info:
			return None
	import_info = clazz["imports"]
	obtained_clazz_list = global_info[type_under_judge] if not in_jdk else jdk_info[type_under_judge]
	for obtained_clazz in obtained_clazz_list:
		obtained_clazz_name = obtained_clazz["name"]
		obtained_clazz_package = obtained_clazz["package"]
		for factor in import_info:
			import_path = factor["path"]
			if_wildcard = factor["if_wildcard"]
			if_static = factor["if_static"]
			if not if_static:
				if if_wildcard:
					real_package = import_path
					if real_package == obtained_clazz_package:
						return real_package + "." + type_under_judge
				else:
					inner_deep = len(obtained_clazz["external_clazzes"])
					real_package = ".".join(import_path.split(".")[:-(1 + inner_deep)])
					clazz_name = import_path.split(".")[-1]
					if real_package == obtained_clazz_package and clazz_name == obtained_clazz_name:
						return real_package + "." + type_under_judge
	return None


def check_type_and_package_in_import(clazz, clazz_under_judge, global_info, jdk_info):
	package_under_judge = clazz_under_judge["package"]
	type_under_judge = clazz_under_judge["name"]
	in_jdk = False
	if type_under_judge not in global_info:
		in_jdk = True
		if type_under_judge not in jdk_info:
			return False
	import_info = clazz["imports"]
	obtained_clazz_list = global_info[type_under_judge] if not in_jdk else jdk_info[type_under_judge]
	for obtained_clazz in obtained_clazz_list:
		obtained_clazz_name = obtained_clazz["name"]
		obtained_clazz_package = obtained_clazz["package"]
		if obtained_clazz_package != package_under_judge:
			continue
		for factor in import_info:
			import_path = factor["path"]
			if_wildcard = factor["if_wildcard"]
			if_static = factor["if_static"]
			if not if_static:
				if if_wildcard:
					real_package = import_path
					if real_package == obtained_clazz_package:
						return True
				else:
					inner_deep = len(obtained_clazz["external_clazzes"])
					real_package = ".".join(import_path.split(".")[:-(1 + inner_deep)])
					clazz_name = import_path.split(".")[-1]
					if real_package == obtained_clazz_package and clazz_name == obtained_clazz_name:
						return True
	return False


def search_in_static_import(clazz, element_name, identifier_name, global_info, jdk_info, is_method):
	import_info = clazz["imports"]
	for factor in import_info:
		import_path = factor["path"]
		if_wildcard = factor["if_wildcard"]
		if_static = factor["if_static"]
		if not if_static:
			continue
		if if_wildcard:
			real_package = ".".join(import_path.split(".")[:-1])
			clazz_name = import_path.split(".")[-1]
			static_element = ""
		else:
			real_package = ".".join(import_path.split(".")[:-2])
			clazz_name = import_path.split(".")[-2]
			static_element = import_path.split(".")[-1]
		# not exactly be imported
		if not if_wildcard and identifier_name != static_element:
			continue
		parts = [global_info, jdk_info]
		if not is_method:
			for part in parts:
				if clazz_name in part:
					for obtained_clazz in part[clazz_name]:
						inner_deep = len(obtained_clazz["external_clazzes"])
						real_package = ".".join(real_package.split(".")[:-inner_deep])
						if obtained_clazz["package"] != real_package:
							continue
						for field in obtained_clazz["fields"]:
							if field["name"] == element_name:
								type = field["type"]
								return type, None
		else:
			for part in parts:
				if clazz_name in part:
					for obtained_clazz in part[clazz_name]:
						inner_deep = len(obtained_clazz["external_clazzes"])
						real_package = ".".join(real_package.split(".")[:-inner_deep])
						if obtained_clazz["package"] != real_package:
							continue
						find_flag = False
						method_type = None
						method_params = []
						for method in obtained_clazz["methods"]:
							if method["name"] == element_name:
								find_flag = True
								method_type = method["type"]
								method_params.append(method["parameters"])
						if find_flag:
							return method_type, method_params
	return None, None


def syntax_checker(expr_list, clazz_name, package_name, local_info, global_info, jdk_info):
	type_info = {}
	method_parameters = {}
	curr_clazz = None
	for clazz in global_info[clazz_name]:
		if clazz["package"] == package_name:
			curr_clazz = clazz
	if not curr_clazz:
		return False, None, None
	for expr in expr_list:
		type = None
		factors = expr.split(".")
		# the first factor needs a special solution
		factor = factors[0]
		# member
		if "(" not in factor:
			if factor == "this":
				type = clazz_name
			elif factor == "super":
				if curr_clazz["super_class"]:
					type = curr_clazz["super_class"][0]
			else:
				if factor in local_info:
					type = local_info[factor]
				else:
					if factor in global_info or factor in jdk_info:
						type = factor
						type = check_type_in_import(curr_clazz, type, global_info, jdk_info)
					if not type:
						type = search_clazz_fields(factor, clazz_name, global_info, jdk_info)
					# import static
					if not type:
						type, _ = search_in_static_import(curr_clazz, factor, factor, global_info, jdk_info, False)
		# method
		else:
			factor_name = factor.split("(")[0]
			if factor_name == "this" or factor_name == "super":
				if len(factors) != 1:
					return False, None, None
			elif factor_name in global_info:
				# constructor
				if len(factors) != 1:
					return False, None, None
			elif factor_name in jdk_info:
				# constructor
				if len(factors) != 1:
					return False, None, None
			else:
				type, parameters = search_clazz_methods(factor, clazz_name, curr_clazz, global_info, jdk_info)
				# import static
				if not type:
					type, parameters = search_in_static_import(curr_clazz, factor, factor_name, global_info, jdk_info, True)
				method_parameters[factor_name] = parameters

		if not type:
			return False, None, None

		# array[] only has one attribute -> "length"
		if "[" in type:
			if len(factors) == 2:
				if factors[1] != "length":
					return False, None, None
			elif len(factors) > 2:
				return False, None, None
		# the solution of other factors
		for i, factor in enumerate(factors[1:]):
			if factor == "this" or factor == "super":
				return False, None, None
			if "(" not in factor:
				type = search_clazz_fields(factor, type, global_info, jdk_info)
			else:
				type, parameters = search_clazz_methods(factor, type, curr_clazz if i == 0 else None, global_info, jdk_info)
				factor_name = factor.split("(")[0]
				method_parameters[factor_name] = parameters
			if not type:
				return False, None, None
		type_info[expr] = type

	return True, type_info, method_parameters


def search_clazz_fields(factor, package, global_info, jdk_info, in_jdk=False, iterator_count=0):
	if iterator_count > 5:
		return None
	clazz_name = package.split(".")[-1]
	# once search in jdk, there is no change to flow back to d4j projects
	parts = [global_info, jdk_info]
	for i, part in enumerate(parts):
		if in_jdk and i == 0:
			continue
		if clazz_name in part:
			clazz_list = part[clazz_name]
			for clazz in clazz_list:
				# forbid regarding itself as the super class
				if "." in package and package[0].islower() and clazz["package"] + "." + clazz["name"] != package:
					continue
				clazz_fields = clazz["fields"]
				for field in clazz_fields:
					if field["name"] == factor:
						return field["type"]
				for super_clazz in clazz["super_class"]:
					type = search_clazz_fields(factor, super_clazz, global_info, jdk_info, True if i == 1 else False, iterator_count+1)
					if type:
						return type
	return None


def search_clazz_methods(factor, package, curr_clazz_object, global_info, jdk_info, in_jdk=False, iterator_count=0):
	if iterator_count > 5:
		return None, None
	clazz_name = package.split(".")[-1]
	factor_name = factor.split("(")[0]
	factor_argument_count = int(factor.split("(")[1].split(")")[0])
	# once search in jdk, there is no change to flow back to d4j projects
	parts = [global_info, jdk_info]
	for i, part in enumerate(parts):
		if in_jdk and i == 0:
			continue
		if clazz_name in part:
			clazz_list = part[clazz_name]
			for clazz in clazz_list:
				# forbid regarding itself as the super class
				if "." in package and package[0].islower() and clazz["package"] + "." + clazz["name"] != package:
					continue
				if curr_clazz_object:
					status = check_type_and_package_in_import(curr_clazz_object, clazz, global_info, jdk_info)
				else:
					status = True
				if not status:
					continue
				clazz_methods = clazz["methods"]
				find_flag = False
				method_type = None
				method_params = []
				for method in clazz_methods:
					if method["name"] == factor_name and len(method["parameters"]) == factor_argument_count:
						find_flag = True
						method_type = method["type"]
						method_params.append(method["parameters"])
				if find_flag:
					return method_type, method_params
				for super_clazz in clazz["super_class"]:
					type, parameters = search_clazz_methods(factor, super_clazz, clazz, global_info, jdk_info, True if i == 1 else False, iterator_count+1)
					if type:
						return type, parameters
			# Object class (base)
			object_clazz_list = jdk_info["Object"]
			object_clazz = None
			for each_clazz in object_clazz_list:
				if each_clazz["package"] == "java.lang":
					object_clazz = each_clazz
					break
			if object_clazz:
				for method in object_clazz["methods"]:
					if method["name"] == factor_name and len(method["parameters"]) == factor_argument_count:
						method_type = method["type"]
						method_params = []
						method_params.append(method["parameters"])
						return method_type, method_params
	return None, None


def get_modified_part(before_method, after_method):
	diff_result = difflib.unified_diff(before_method.splitlines(), after_method.splitlines())
	newly_added_part = []
	add_lines = []
	deleted_lines = []
	for line in diff_result:
		if line.startswith("+") and not line.startswith("++"):
			real_line = line[1:].strip()
			if real_line.strip():
				add_lines.append(real_line.strip())
			if not real_line:
				continue
			if real_line == "}":
				continue
			elif real_line.endswith("{"):
				if real_line.startswith("else if"):
					newly_added_part.append(real_line[5:] + ";}")
				if real_line == "}else{":
					continue
				else:
					newly_added_part.append(real_line + ";}")
			elif real_line.startswith("}catch"):
				newly_added_part.append("try {;" + real_line)
			elif real_line.startswith("case") and real_line.endswith(":"):
				newly_added_part.append("switch ( rank2fixspecial ) { " + real_line + " break; }")
			else:
				newly_added_part.append(real_line)
		elif line.startswith("-") and not line.startswith("--"):
			real_line = line[1:].strip()
			if real_line.strip():
				deleted_lines.append(real_line.strip())
	# move stmt
	if sorted(add_lines) == sorted(deleted_lines):
		return ""

	# modify the first line of method
	if len(deleted_lines) == 1 and deleted_lines[0] == before_method.splitlines()[0].strip():
		fake_class = "public class Tmp { \n" + "\n".join(newly_added_part) + "\n}"
		return fake_class
	if not newly_added_part:
		return ""
	else:
		fake_class = "public class Tmp { \npublic void foo () {\n" + "\n".join(newly_added_part) + "\n}\n}"
		# print(fake_class)
		return fake_class


def get_method_invocation(node, method_list):
	if not node:
		return
	elif type(node).__name__ == "list":
		for factor in node:
			get_method_invocation(factor, method_list)
		return
	elif type(node).__name__ == "set":
		for factor in node:
			get_method_invocation(factor, method_list)
		return
	elif type(node).__name__ == "str":
		return
	elif type(node).__name__ == "bool":
		return
	else:
		if type(node).__name__ == "MethodInvocation":
			method_name = node.member
			obtained_args = []
			for arg in node.arguments:
				if type(arg).__name__ == "Literal":
					if arg.value.startswith("\""):
						obtained_args.append("String")
					elif arg.value[0].isdigit() or arg.value[0].isdigit() or arg.value[0] == ".":
						obtained_args.append("number_set")
					elif arg.value == "false" or arg.value == "true":
						obtained_args.append("boolean")
					elif arg.value.startswith("'"):
						obtained_args.append("char")
					elif arg.value == "null":
						obtained_args.append("null")
				else:
					expr_list = parse_specific_node(arg)[0]
					obtained_args.append(expr_list[0] if expr_list else None)
			method_list.append((method_name, obtained_args))
		for i, child in enumerate(node.children):
			get_method_invocation(child, method_list)


def check_method_params(method, type_info, method_params):
	tokens = javalang.tokenizer.tokenize(method)
	parser = javalang.parse.Parser(tokens)
	root = parser.parse()
	method_and_params = []
	get_method_invocation(root, method_and_params)
	for method_name, args in method_and_params:
		if method_name not in method_params:
			continue
		curr_standard_params = method_params[method_name]
		external_flag = False
		for cand_set in curr_standard_params:
			if len(cand_set) != len(args):
				continue
			flag = True
			for i, arg in enumerate(args):
				if arg in ["null"]:
					continue
				if arg in ["byte", "short", "long", "int", "float", "double"]:
					if cand_set[i] != "number_set":
						flag = False
						break
				elif arg == "char":
					if cand_set[i] not in ["char", "String"]:
						flag = False
						break
				elif arg in ["boolean", "String"]:
					if cand_set[i] != arg:
						flag = False
						break
				else:
					if type_info and arg in type_info:
						if type_info[arg] != cand_set[i] and cand_set[i] not in ["Object", "T", "K", "V", "E"]:
							flag = False
							break
			if flag:
				external_flag = True
				break
		if not external_flag:
			return False
	return True


def get_binary_expr(node, binary_exprs):
	if not node:
		return
	elif type(node).__name__ == "list":
		for factor in node:
			get_binary_expr(factor, binary_exprs)
		return
	elif type(node).__name__ == "set":
		for factor in node:
			get_binary_expr(factor, binary_exprs)
		return
	elif type(node).__name__ == "str":
		return
	elif type(node).__name__ == "bool":
		return
	else:
		if type(node).__name__ == "BinaryOperation":
			operator = node.operator
			op1 = node.operandl
			op2 = node.operandr
			parts = [op1, op2]
			types = []
			for part in parts:
				if type(part).__name__ == "Literal":
					if part.value.startswith("\""):
						types.append("String")
					elif part.value.isdigit() or part.value[0].isdigit() or part.value[0] == ".":
						types.append("number_set")
					elif part.value == "false" or part.value == "true":
						types.append("boolean")
					elif part.value.startswith("'"):
						types.append("char")
					elif part.value == "null":
						types.append("null")
					else:
						print(part.value)
						exit(0)
				elif type(part).__name__ == "BinaryOperation":
					if part.operator in ["==", "!=", ">=", "<=", ">", "<", "&&", "||"]:
						types.append("boolean")
					else:
						expr_list = parse_specific_node(part)[0]
						types.append(expr_list[0] if expr_list else None)
				else:
					expr_list = parse_specific_node(part)[0]
					types.append(expr_list[0] if expr_list else None)
			binary_exprs.append((operator, types[0], types[1]))
		for i, child in enumerate(node.children):
			get_binary_expr(child, binary_exprs)


def check_binary_operations(method, type_info):
	tokens = javalang.tokenizer.tokenize(method)
	parser = javalang.parse.Parser(tokens)
	root = parser.parse()
	binary_exprs = []
	base_types = ["byte", "short", "int", "long", "float", "double", "char", "String", "boolean"]
	get_binary_expr(root, binary_exprs)
	for expr in binary_exprs:
		operator, op1, op2 = expr
		if op1 not in base_types:
			if type_info and op1 in type_info:
				op1 = type_info[op1]
		if op2 not in base_types:
			if type_info and op2 in type_info:
				op2 = type_info[op2]
		if not op1 or not op2:
			continue
		flag = False
		if op1 == "void" or op2 == "void":
			return False
		elif operator in ["-", "*", "/", "%", ">", "<", ">=", "<="]:
			if op1 in ["byte", "short", "int", "long", "float", "double", "char", "number_set"] and \
				op2 in ["byte", "short", "int", "long", "float", "double", "char", "number_set"]:
				flag = True
		elif operator == "+":
			if op1 in ["byte", "short", "int", "long", "float", "double", "char", "String", "number_set"] and \
				op2 in ["byte", "short", "int", "long", "float", "double", "char", "String", "number_set"]:
				flag = True
		elif operator in ["&&", "||"]:
			if op1 == "boolean" and op2 == "boolean":
				flag = True
		elif operator in ["|", "&", "^", "<<", ">>", ">>>"]:
			if op1 in ["byte", "short", "int", "long", "char", "number_set"] and \
				op2 in ["byte", "short", "int", "long", "char", "number_set"]:
				flag = True
		elif operator in ["!=", "=="]:
			if op1 == "null":
				if op2 not in ["byte", "short", "int", "long", "float", "double", "char", "boolean", "number_set"]:
					flag = True
			elif op2 == "null":
				if op1 not in ["byte", "short", "int", "long", "float", "double", "char", "boolean", "number_set"]:
					flag = True
			else:
				flag = True
		else:
			flag = True
		if not flag:
			return False
	return True


def get_assign_and_vardecl(node, elements):
	if not node:
		return
	elif type(node).__name__ == "list":
		for factor in node:
			get_assign_and_vardecl(factor, elements)
		return
	elif type(node).__name__ == "set":
		for factor in node:
			get_assign_and_vardecl(factor, elements)
		return
	elif type(node).__name__ == "str":
		return
	elif type(node).__name__ == "bool":
		return
	else:
		if type(node).__name__ == "Assignment" or type(node).__name__ == "VariableDeclarator":
			if type(node).__name__ == "Assignment":
				operator = node.type
				left = node.expressionl
				right = node.value
			else:
				operator = "="
				left = node.name
				right = node.initializer
			parts = [left, right]
			types = []
			for part in parts:
				if type(part).__name__ == "Literal":
					if part.value.startswith("\""):
						types.append("String")
					elif part.value.isdigit() or part.value[0].isdigit() or part.value[0] == ".":
						types.append("number_set")
					elif part.value == "false" or part.value == "true":
						types.append("boolean")
					elif part.value.startswith("'"):
						types.append("char")
					elif part.value == "null":
						types.append("null")
					else:
						print(part.value)
						exit(0)
				elif type(part).__name__ == "BinaryOperation":
					if part.operator in ["==", "!=", ">=", "<=", ">", "<", "&&", "||"]:
						types.append("boolean")
					else:
						expr_list = parse_specific_node(part)[0]
						types.append(expr_list[0] if expr_list else None)
				else:
					expr_list = parse_specific_node(part)[0]
					types.append(expr_list[0] if expr_list else None)
			elements.append((operator, types[0], types[1]))
		for i, child in enumerate(node.children):
			get_assign_and_vardecl(child, elements)


def check_assignment_and_vardecl(method, type_info):
	tokens = javalang.tokenizer.tokenize(method)
	parser = javalang.parse.Parser(tokens)
	root = parser.parse()
	elements = []
	base_types = ["byte", "short", "int", "long", "float", "double", "char", "String", "boolean", "null"]
	get_assign_and_vardecl(root, elements)
	for expr in elements:
		operator, op1, op2 = expr
		if op1 not in base_types:
			if type_info and op1 in type_info:
				op1 = type_info[op1]
		if op2 not in base_types:
			if type_info and op2 in type_info:
				op2 = type_info[op2]
		if not op1 or not op2:
			continue
		flag = False
		if operator == "=":
			if op1 in ["byte", "short", "int", "long", "float", "double", "char", "number_set"] and \
					op2 in ["byte", "short", "int", "long", "float", "double", "char", "number_set"]:
				flag = True
			elif op1 == "null" or op2 == "null" or op1 == op2:
				flag = True
		# for +=, -=, *=, /=, %=, only number types are compatible
		else:
			if op1 == "+=":
				if op1 in ["byte", "short", "int", "long", "float", "double", "char", "String", "number_set", "String"] and \
					op2 in ["byte", "short", "int", "long", "float", "double", "char", "String", "number_set", "String"]:
					flag = True
			else:
				if op1 in ["byte", "short", "int", "long", "float", "double", "char", "String", "number_set"] and \
					op2 in ["byte", "short", "int", "long", "float", "double", "char", "String", "number_set"]:
					flag = True
		if not flag:
			return False
	return True


def get_array_index(node, elements):
	if not node:
		return
	elif type(node).__name__ == "list":
		for factor in node:
			get_array_index(factor, elements)
		return
	elif type(node).__name__ == "set":
		for factor in node:
			get_array_index(factor, elements)
		return
	elif type(node).__name__ == "str":
		return
	elif type(node).__name__ == "bool":
		return
	else:
		if type(node).__name__ == "ArraySelector":
			array_index = node.index
			if type(array_index).__name__ == "Literal":
				if array_index.value.isdigit() or array_index.value[0].isdigit() or array_index.value[0] == ".":
					if "." in array_index.value:
						index_type = "point_number"
					else:
						index_type = "no_point_number"
				else:
					index_type = "no_number"
			elif type(array_index).__name__ == "BinaryOperation":
				if array_index.operator in ["==", "!=", ">=", "<=", ">", "<", "&&", "||"]:
					index_type = "no_number"
				else:
					expr_list = parse_specific_node(array_index)[0]
					index_type = expr_list[0] if expr_list else None
			else:
				expr_list = parse_specific_node(array_index)[0]
				index_type = expr_list[0] if expr_list else None
			elements.append(index_type)
		if type(node).__name__ == "ArrayCreator":
			for dim in node.dimensions:
				if type(dim).__name__ == "MemberReference":
					expr_list = parse_specific_node(dim)[0]
					index_type = expr_list[0] if expr_list else None
					elements.append(index_type)
		for i, child in enumerate(node.children):
			get_array_index(child, elements)


def check_array_index(method, type_info):
	tokens = javalang.tokenizer.tokenize(method)
	parser = javalang.parse.Parser(tokens)
	root = parser.parse()
	elements = []
	base_types = ["point_number", "no_point_number", "no_number"]
	get_array_index(root, elements)
	for arrry_index in elements:
		if arrry_index not in base_types:
			if type_info and arrry_index in type_info:
				arrry_index = type_info[arrry_index]
		if not arrry_index:
			continue
		if arrry_index not in ["byte", "short", "int", "long", "no_point_number"]:
			return False
	return True


def get_unary_exprs(node, elements):
	if not node:
		return
	elif type(node).__name__ == "list":
		for factor in node:
			get_unary_exprs(factor, elements)
		return
	elif type(node).__name__ == "set":
		for factor in node:
			get_unary_exprs(factor, elements)
		return
	elif type(node).__name__ == "str":
		return
	elif type(node).__name__ == "bool":
		return
	else:
		operators = []
		if hasattr(node, "prefix_operators") and node.prefix_operators:
			operators += node.prefix_operators
		if hasattr(node, "postfix_operators") and node.postfix_operators:
			operators += node.postfix_operators
		if operators:
			if type(node).__name__ == "Literal":
				if node.value.isdigit() or node.value[0].isdigit() or node.value[0] == ".":
					expr_type = "number_set"
				elif node.value == "false" or node.value == "true":
					expr_type = "boolean"
				else:
					expr_type = "others"
			elif type(node).__name__ == "BinaryOperation":
				if node.operator in ["==", "!=", ">=", "<=", ">", "<", "&&", "||"]:
					expr_type = "boolean"
				else:
					expr_list = parse_specific_node(node)[0]
					expr_type = expr_list[0] if expr_list else None
			else:
				expr_list = parse_specific_node(node)[0]
				expr_type = expr_list[0] if expr_list else None
			elements.append((operators, expr_type))
		for i, child in enumerate(node.children):
			get_unary_exprs(child, elements)


def check_unary_expr(method, type_info):
	tokens = javalang.tokenizer.tokenize(method)
	parser = javalang.parse.Parser(tokens)
	root = parser.parse()
	elements = []
	base_types = ["number_set", "boolean", "others"]
	get_unary_exprs(root, elements)
	for operators, expr in elements:
		if expr not in base_types:
			if type_info and expr in type_info:
				expr = type_info[expr]
		if not expr:
			continue
		if "!" in operators:
			if expr != "boolean":
				return False
		if "++" in operators or "--" in operators:
			if expr not in ["number_set", "byte", "short", "int", "long", "double", "float", "char"]:
				return False
	return True


def parse_if_all_in_loop(node, in_loop):
	if not node:
		pass
	elif type(node).__name__ == "list":
		for factor in node:
			status = parse_if_all_in_loop(factor, in_loop)
			if not status:
				return False
	elif type(node).__name__ == "set":
		for factor in node:
			status = parse_if_all_in_loop(factor, in_loop)
			if not status:
				return False
	elif type(node).__name__ == "str":
		pass
	elif type(node).__name__ == "bool":
		pass
	else:
		if type(node).__name__ == "WhileStatement" or type(node).__name__ == "ForStatement" or \
				type(node).__name__ == "DoStatement" or type(node).__name__ == "SwitchStatement":
			in_loop = True
		elif type(node).__name__ == "ContinueStatement" or type(node).__name__ == "BreakStatement":
			if not in_loop:
				return False
		for child in node.children:
			status = parse_if_all_in_loop(child, in_loop)
			if not status:
				return False
	return True


def check_continue_and_break(method):
	fake_clazz = "public class Tmp { \n" + method + "\n}"
	tokens = javalang.tokenizer.tokenize(fake_clazz)
	parser = javalang.parse.Parser(tokens)
	root = parser.parse()
	return parse_if_all_in_loop(root, in_loop=False)


def parse_ternary_expression(node, elements):
	if type(node.if_true).__name__ == "TernaryExpression":
		parse_ternary_expression(node.if_true, elements)
	else:
		elements.append(node.if_true)
	if type(node.if_false).__name__ == "TernaryExpression":
		parse_ternary_expression(node.if_false, elements)
	else:
		elements.append(node.if_false)


def get_return_exprs(node, elements):
	if not node:
		return
	elif type(node).__name__ == "list":
		for factor in node:
			get_return_exprs(factor, elements)
		return
	elif type(node).__name__ == "set":
		for factor in node:
			get_return_exprs(factor, elements)
		return
	elif type(node).__name__ == "str":
		return
	elif type(node).__name__ == "bool":
		return
	else:
		if type(node).__name__ == "ReturnStatement":
			if not node.expression:
				expr_type = "void"
			else:
				expr = node.expression
				if type(expr).__name__ == "TernaryExpression":
					ternary_elements = []
					parse_ternary_expression(expr, ternary_elements)
					expr = ternary_elements[0]
				if type(expr).__name__ == "Literal":
					if expr.value.startswith("\""):
						expr_type = "String"
					elif expr.value.isdigit() or expr.value[0].isdigit() or expr.value[0] == ".":
						expr_type = "number_set"
					elif expr.value == "false" or expr.value == "true":
						expr_type = "boolean"
					elif expr.value.startswith("'"):
						expr_type = "char"
					elif expr.value == "null":
						expr_type = "null"
					else:
						expr_type = None
						print(expr.value)
						exit(0)
				elif type(expr).__name__ == "BinaryOperation":
					if expr.operator in ["==", "!=", ">=", "<=", ">", "<", "&&", "||"]:
						expr_type = "boolean"
					else:
						expr_list = parse_specific_node(expr)[0]
						expr_type = expr_list[0] if expr_list else None
				else:
					expr_list = parse_specific_node(expr)[0]
					expr_type = expr_list[0] if expr_list else None
			elements.append(expr_type)
			return
		for child in node.children:
			get_return_exprs(child, elements)


def check_return_type(method, type_info, corresponding_method):
	fake_clazz = "public class Tmp {\n" + corresponding_method + "\n}"
	tokens = javalang.tokenizer.tokenize(fake_clazz)
	parser = javalang.parser.Parser(tokens)
	root = parser.parse()
	try:
		method_node = root.types[0].methods[0]
	except:
		return True
	if method_node.return_type:
		method_return_type = method_node.return_type.name + "[]" * len(method_node.return_type.dimensions)
	else:
		method_return_type = "void"
	# search all return statements
	tokens = javalang.tokenizer.tokenize(method)
	parser = javalang.parse.Parser(tokens)
	root = parser.parse()
	elements = []
	base_types = ["byte", "short", "int", "long", "float", "double", "String", "char", "boolean", "null", "number_set"]
	get_return_exprs(root, elements)
	for element in elements:
		if element not in base_types:
			if type_info and element in type_info:
				element = type_info[element]
		if not element:
			continue
		if element == "null":
			if method_return_type in ["byte", "short", "int", "long", "float", "double", "char", "boolean", "void"]:
				return False
		elif element != method_return_type:
			return False
	return True


def check_if_basic_type_be_dereferenced(expr_list):
	for expr in expr_list:
		element_list = expr.split(".")
		for element in element_list:
			if element in ["byte", "short", "int", "long", "float", "double", "char", "boolean", "void"]:
				return False
	return True


def get_cast_types(node, elements):
	if not node:
		return
	elif type(node).__name__ == "list":
		for factor in node:
			get_cast_types(factor, elements)
		return
	elif type(node).__name__ == "set":
		for factor in node:
			get_cast_types(factor, elements)
		return
	elif type(node).__name__ == "str":
		return
	elif type(node).__name__ == "bool":
		return
	else:
		if type(node).__name__ == "Cast":
			cast_type = node.type
			elements.append(cast_type)
		for i, child in enumerate(node.children):
			get_cast_types(child, elements)


def check_if_cast_type_is_clazz(method, global_info, jdk_info):
	tokens = javalang.tokenizer.tokenize(method)
	parser = javalang.parse.Parser(tokens)
	root = parser.parse()
	elements = []
	get_cast_types(root, elements)
	for element in elements:
		if type(element).__name__ == "ReferenceType":
			type_name = element.name
			if not (type_name in global_info or type_name in jdk_info):
				return False
		elif type(element).__name__ == "BasicType":
			# correct
			pass
		else:
			return False
	return True


def get_cond_exprs(node, elements):
	if not node:
		return
	elif type(node).__name__ == "list":
		for factor in node:
			get_cond_exprs(factor, elements)
		return
	elif type(node).__name__ == "set":
		for factor in node:
			get_cond_exprs(factor, elements)
		return
	elif type(node).__name__ == "str":
		return
	elif type(node).__name__ == "bool":
		return
	else:
		found_element = None
		if type(node).__name__ == "WhileStatement":
			cond_expr = node.condition
			if type(cond_expr).__name__ != "BinaryOperation":
				found_element = cond_expr
		elif type(node).__name__ == "ForStatement":
			control_expr = node.control
			if hasattr(control_expr, "condition"):
				cond_expr = control_expr.condition
				if type(cond_expr).__name__ != "BinaryOperation":
					found_element = cond_expr
		elif type(node).__name__ == "IfStatement":
			cond_expr = node.condition
			if type(cond_expr).__name__ != "BinaryOperation":
				found_element = cond_expr
		elif type(node).__name__ == "DoStatement":
			cond_expr = node.condition
			if type(cond_expr).__name__ != "BinaryOperation":
				found_element = cond_expr
		if found_element:
			if type(found_element).__name__ == "Literal":
				if found_element.value == "false" or found_element.value == "true":
					elements.append("boolean")
				else:
					elements.append("no_boolean")
			else:
				expr_list = parse_specific_node(found_element)[0]
				elements.append(expr_list[0] if expr_list else None)
		for i, child in enumerate(node.children):
			get_cond_exprs(child, elements)


def check_cond_expr(method, type_info):
	tokens = javalang.tokenizer.tokenize(method)
	parser = javalang.parse.Parser(tokens)
	root = parser.parse()
	elements = []
	get_cond_exprs(root, elements)
	base_types = ["boolean", "no_boolean"]
	for element in elements:
		if element not in base_types:
			if type_info and element in type_info:
				element = type_info[element]
		if not element:
			continue
		if element != "boolean":
			return False
	return True


def get_same_block_statements(node, elements):
	if not node:
		return
	elif type(node).__name__ == "list":
		elements.append(node)
		for factor in node:
			get_same_block_statements(factor, elements)
		return
	elif type(node).__name__ == "set":
		for factor in node:
			get_same_block_statements(factor, elements)
		return
	elif type(node).__name__ == "str":
		return
	elif type(node).__name__ == "bool":
		return
	else:
		for i, child in enumerate(node.children):
			get_same_block_statements(child, elements)


def check_unreachable_statement(method):
	fake_clazz = "public class Tmp {\n" + method + "\n}"
	tokens = javalang.tokenizer.tokenize(fake_clazz)
	parser = javalang.parse.Parser(tokens)
	root = parser.parse()
	elements = []
	get_same_block_statements(root, elements)
	for element in elements:
		end_flag = False
		for factor in element:
			# in the same block, the following statements are not the final one
			if end_flag:
				return False
			if type(factor).__name__ == "ContinueStatement" or type(factor).__name__ == "BreakStatement" or \
				type(factor).__name__ == "ReturnStatement" or type(factor).__name__ == "ThrowStatement":
				end_flag = True
	return True


if __name__ == "__main__":
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]
	BEAM = int(sys.argv[4])
	TEMPLATE_SIZE = int(sys.argv[5])
	SINGLE_SIZE = int(sys.argv[6])

	parsed_data_dir = "../../parsed_data/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version)
	out_dir = os.path.join(parsed_data_dir, "result/")
	input_path = os.path.join(out_dir, "patches_without_unk.pkl")
	sample_info_path = os.path.join(parsed_data_dir, "completion_info/sample_info.txt")
	clazz_name_info_path = os.path.join(parsed_data_dir, "clazz_name.txt")
	clazz_package_info_path = os.path.join(parsed_data_dir, "clazz_package_name.txt")
	local_info_path = os.path.join(parsed_data_dir, "completion_info/local_info.pkl")
	global_info_path = os.path.join(parsed_data_dir, "inner_and_third_party.pkl")
	method_data_dir = os.path.join(parsed_data_dir, "data_no_empty_without_anno/")
	out_path = os.path.join(out_dir, "patches_final.pkl")
	with open(input_path, "rb") as file:
		candidates = pickle.load(file)
	with open(sample_info_path, "r") as file:
		sample_info = file.readlines()
	with open(local_info_path, "rb") as file:
		local_info = pickle.load(file)
	with open(clazz_name_info_path, "r") as file:
		clazz_name_seq = file.readlines()
		clazz_name_seq = [factor.strip() for factor in clazz_name_seq]
	with open(clazz_package_info_path, "r") as file:
		clazz_package_name_seq = file.readlines()
		clazz_package_name_seq = [factor.strip() for factor in clazz_package_name_seq]
	method_no_anno_data = []
	for i in range(1, len(os.listdir(method_data_dir)) + 1):
		with open(os.path.join(method_data_dir, "{}.txt".format(i)), "r") as file:
			method_no_anno_data.append(file.read())
	version_seq = []
	for factor in sample_info:
		version_info = factor.strip().split(",")[0]
		version_seq.append(version_info)
	with open(os.path.join(parsed_data_dir, "jdk_info.pkl"), "rb") as file:
		jdk_info = pickle.load(file)
	# end_index = len(version_seq)
	output = []
	for cursor in range(len(version_seq)):
		already_cands = []
		curr_version = version_seq[cursor]
		curr_clazz_name = clazz_name_seq[cursor]
		curr_package_name = clazz_package_name_seq[cursor]
		curr_candidates = candidates[cursor * BEAM: (cursor + 1) * BEAM]
		curr_local_info = local_info[cursor]
		with open(global_info_path, "rb") as file:
			curr_global_info = pickle.load(file)
		for i, cand in enumerate(curr_candidates):
			curr_output = []
			skip_num = 0
			for factor in cand:
				if len(curr_output) + skip_num >= 3:
					break
				if factor in already_cands:
					skip_num += 1
					continue
				else:
					already_cands.append(factor)
				if not check_method_syntax_correct(factor):
					continue
				if i < TEMPLATE_SIZE + SINGLE_SIZE:
					# normalize lines
					before_method = "\n".join([line.strip() for line in method_no_anno_data[cursor].splitlines()])
					after_method = "\n".join([line.strip() for line in factor.splitlines()])
					factor_with_specific_part = get_modified_part(before_method, after_method)
				else:
					factor_with_specific_part = factor
				if not factor_with_specific_part:
					curr_output.append(factor)
					continue
				expr_list, if_syntax_correct, factor_with_specific_part = get_expr(factor_with_specific_part, factor)
				if not if_syntax_correct:
					continue
				if "rank2fixspecial" in expr_list:
					expr_list.remove("rank2fixspecial")
				status, type_info, method_params = syntax_checker(expr_list, curr_clazz_name, curr_package_name, curr_local_info, curr_global_info, jdk_info)
				if status:
					if not method_params:
						status = True
					else:
						status = check_method_params(factor_with_specific_part, type_info, method_params)
				if status:
					status = check_binary_operations(factor_with_specific_part, type_info)
				if status:
					status = check_assignment_and_vardecl(factor_with_specific_part, type_info)
				if status:
					status = check_array_index(factor_with_specific_part, type_info)
				if status:
					status = check_unary_expr(factor_with_specific_part, type_info)
				if status:
					status = check_continue_and_break(factor)
				if status:
					status = check_return_type(factor_with_specific_part, type_info, factor)
				if status:
					status = check_if_basic_type_be_dereferenced(expr_list)
				if status:
					status = check_if_cast_type_is_clazz(factor_with_specific_part, curr_global_info, jdk_info)
				if status:
					status = check_cond_expr(factor_with_specific_part, type_info)
				if status:
					status = check_unreachable_statement(factor)
				if status:
					curr_output.append(factor)
			output.append(curr_output)
		cursor += 1
	with open(out_path, "wb") as file:
		pickle.dump(output, file)
