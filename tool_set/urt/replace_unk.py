import javalang
from gen_ast import gen_ast
from parse_unk_type import parse_unk_type
from find_gredients import *
from utils import *
import random
import difflib
import re
import string


def solve_camel_and_underline(token):
	if token.isdigit():
		return [token]
	else:
		p = re.compile(r'([a-z]|\d)([A-Z])')
		sub = re.sub(p, r'\1_\2', token).lower()
		sub_tokens = sub.split("_")
		tokens = re.sub(" +", " ", " ".join(sub_tokens)).strip()
		final_token = []
		for factor in tokens.split(" "):
			final_token.append(factor.rstrip(string.digits))
		return final_token


def replace_unk_from_origin(node, src_code, unk_type, already_selected_candidates):
	candidate = None
	ast_path = []
	while node.name != "<root>":
		node_index = node.parent.children.index(node)
		node_name = node.name
		ast_path.append((node_index, node_name))
		node = node.parent
	ast_path = ast_path[::-1]  # reverse
	src_code = src_code.replace("rank2fixstart", "").replace("rank2fixend", "")
	fake_code = "public class Tmp { " + src_code + " }"
	try:
		tokens = javalang.tokenizer.tokenize(fake_code)
		parser = javalang.parser.Parser(tokens)
		root = parser.parse()
		root_node = gen_ast(root)
		node = root_node
		ast_recover_flag = True
		variable_to_literal_flag = False  # use a literal to replace <unk>, because some literals are too rare to exist in vocab
		child_index = -1
		for step_index in range(len(ast_path) - 1):  # the last one is <unk>
			step = ast_path[step_index]
			child_index = step[0]
			child_name = step[1]
			flag = False
			if child_index < len(node.children):
				child_node = node.children[child_index]
				if child_node.name == child_name:
					flag = True
					node = child_node
				else:  # use a same-position literal to replace <unk>
					if child_node.name == "Literal" and child_name == "MemberReference":
						variable_to_literal_flag = True
						node = child_node
						continue
					if variable_to_literal_flag:
						if child_name == "member":
							for child_factor in node.children:
								if child_factor.name == "value":
									node = child_factor
									flag = True
									break
						if not flag:  # recover to the position while difference firstly occurs
							node = node.parent
							child_index = ast_path[step_index - 1][0]
							child_name = ast_path[step_index - 1][1]
			if not flag:
				src_same_indices = []
				for child_node in node.children:
					if child_node.name == child_name:
						flag = True
						src_same_indices.append(node.children.index(child_node))
				nearest_index = -1
				shortest_distance = 1e3
				for index in src_same_indices:
					if abs(index - child_index) < shortest_distance:
						nearest_index = index
						shortest_distance = abs(index - child_index)
				if nearest_index != -1:
					node = node.children[nearest_index]
			if not flag:
				# print("Cannot find the corresponding ast path")
				ast_recover_flag = False
				break
		if ast_recover_flag:
			last_step = ast_path[-1]
			last_node_index = last_step[0]
			if last_node_index < len(node.children):
				candidate = node.children[last_node_index].name
		else:
			# while node and not candidate:
			candidate_list = []
			if child_index < len(node.children):  # give a high priority for same relative position node
				find_ingredient(unk_type, node.children[child_index], candidate_list)
				for index in range(len(node.children)):  # then parse other nodes with different positions
					if index != child_index:
						find_ingredient(unk_type, node.children[index], candidate_list)
			else:  # just parse all nodes in a naive way
				find_ingredient(unk_type, node, candidate_list)
			if candidate_list:
				# print("length: {}".format(len(candidate_list)))
				current_already_used_candidates = []
				current_not_used_candidates = []
				for factor in candidate_list:
					if factor in already_selected_candidates:
						current_already_used_candidates.append(factor)
					else:
						current_not_used_candidates.append(factor)
				candidate_list = current_not_used_candidates + current_already_used_candidates
				candidate = candidate_list[0]
	except (javalang.parser.JavaSyntaxError, UnicodeDecodeError):
		pass
	if not candidate:
		print("==========")

	return candidate


def find_ingredient(unk_type, node, candidate_list):
	if unk_type == "method_member":
		find_method_members(node, candidate_list)
	elif unk_type == "method_qualifier":
		find_method_qualifiers(node, candidate_list)
	elif unk_type == "variable_member":
		find_variable_members(node, candidate_list)
	elif unk_type == "variable_qualifier":
		find_variable_qualifiers(node, candidate_list)
	elif unk_type == "variable_dec_name":
		find_variable_decl_names(node, candidate_list)
	elif unk_type == "method_dec_name":
		candidate = find_method_decl_name(node)
	elif unk_type == "type_name":
		find_type_names(node, candidate_list)
	elif unk_type == "return_type":
		candidate = find_return_type(node)
	elif unk_type == "parameter_name":
		find_parameter_names(node, candidate_list)
	elif unk_type == "constructor_dec_name":
		candidate = find_constructor_decl_name(node)
	elif unk_type == "this_method_member":
		find_this_method_members(node, candidate_list)
	elif unk_type == "this_variable_member":
		find_this_variable_members(node, candidate_list)


def replace_for_totally_same(pred_tgt, origin_stmt, pre_code, post_code, global_info, local_info, extra_global_info, replace_list):
	unk_indices = []
	for index, factor in enumerate(pred_tgt.split(" ")):
		if factor == "<unk>":
			unk_indices.append(index)
	if len(unk_indices) == 0:
		tokens = javalang.tokenizer.tokenize(pred_tgt)
		for index, token in enumerate(tokens):
			if type(token).__name__ == "Identifier":
				unk_indices.append(index)
	if len(unk_indices) == 0:
		return None
	else:
		random.seed(666)
		random.shuffle(unk_indices)
		origin_indices = [i for i in range(len(unk_indices))]
		random.seed(666)
		random.shuffle(origin_indices)
		candidate = None
		for i, index in enumerate(unk_indices):
			fake_stmt = origin_stmt.split(" ")
			fake_stmt[index] = "rank2fixunk"
			fake_method = " ".join(pre_code + fake_stmt + post_code)
			fake_stmt_string = " ".join(fake_stmt)
			fake_class = "public class Tmp { " + fake_method + " }"
			tokens = javalang.tokenizer.tokenize(fake_class)
			parser = javalang.parser.Parser(tokens)
			root = parser.parse()
			root_node = gen_ast(root)
			unk_list = []
			find_unk_nodes(root_node, unk_list)
			assert len(unk_list) == 1
			unk_node = unk_list[0]
			unk_type = parse_unk_type(unk_node)

			current_class = "PLACEHOLDER"
			for key in global_info:
				if global_info[key]["if_current_class"]:
					current_class = key
					break

			origin_factor = origin_stmt.split(" ")[index]
			replace_candidates = []
			boolean_literal_flag = False
			if unk_type == "method_member":
				replace_method_member(unk_node, local_info, global_info, current_class, replace_candidates)
			elif unk_type == "method_qualifier":
				replace_method_qualifier(unk_node, local_info, global_info, current_class, replace_candidates, extra_global_info)
			elif unk_type == "variable_member":
				if origin_factor == "false":
					boolean_literal_flag = True
					replace_candidates.append("true")
				elif origin_factor == "true":
					boolean_literal_flag = True
					replace_candidates.append("false")
				replace_variable_member(unk_node, local_info, global_info, current_class, replace_candidates)
			elif unk_type == "variable_qualifier":
				replace_variable_qualifier(unk_node, local_info, global_info, current_class, replace_candidates)
			elif unk_type == "this_method_member":
				pass
			elif unk_type == "this_variable_member":
				pass
			elif unk_type == "super_method_member":
				pass
			elif unk_type == "super_variable_member":
				pass
			elif unk_type == "type_name":
				replace_candidates = [key for key in global_info]

			if origin_factor in replace_candidates:
				replace_candidates.remove(origin_factor)
			if replace_candidates:

				replace_list[origin_indices[i]] = replace_candidates

				# term frequency
				# term_frequency = {}
				# for factor in replace_candidates:
				# 	term_frequency[factor] = 0

				# for token in origin_stmt.split(" "):  # just stmt
				# for token in pre_code:  # just pre code
				# for token in post_code:  # just post code
				# for token in pre_code + origin_stmt.split(" "):  # pre + stmt
				# for token in origin_stmt.split(" ") + post_code:  # stmt + post

				# for token in pre_code + origin_stmt.split(" ") + post_code:  # pre + stmt + post
				# 	if token in term_frequency:
				# 		term_frequency[token] += 1
				# sorted_list = sorted(term_frequency.items(), key=lambda x: x[1], reverse=True)
				# most_possible_candidate = sorted_list[0][0]

				# calculate similarities of two tokens
				# similarities = {}
				# for factor in replace_candidates:
				# 	similarities[factor] = difflib.SequenceMatcher(None, origin_factor, factor).ratio()
				# sorted_list = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
				# most_possible_candidate = sorted_list[0][0]

				# calculate num of same sub-tokens
				similarities = []
				for factor in replace_candidates:
					factor_list = solve_camel_and_underline(factor)
					origin_factor_list = solve_camel_and_underline(origin_factor)
					insection = [t for t in factor_list if t in origin_factor_list]
					standard_1 = len(insection)
					standard_2 = len(factor_list)
					standard_3 = len(factor)
					similarities.append((factor, standard_1, standard_2, standard_3))
				sorted_list = sorted(similarities, key=lambda x: (-x[1], x[2], x[3]))
				if boolean_literal_flag:
					if "true" in sorted_list:
						sorted_list.remove("true")
						sorted_list = ["true"] + sorted_list
					elif "false" in sorted_list:
						sorted_list.remove("false")
						sorted_list = ["false"] + sorted_list
				most_possible_candidate = sorted_list[0][0]

				# random
				# random.seed(5)
				# random.shuffle(replace_candidates)
				# most_possible_candidate = replace_candidates[0]

				candidate = fake_stmt_string.replace("rank2fixunk", most_possible_candidate)
				break
		if candidate:
			return [candidate]
		else:
			return None


def replace_for_also_unk(pred_tgt, origin_stmt, pre_code, post_code, global_info, local_info, extra_global_info, replace_list):
	fake_stmt = pred_tgt
	fake_stmt = fake_stmt.replace("<also_unk>", "rank2fixunk")
	fake_stmt = fake_stmt.split(" ")
	fake_method = " ".join(pre_code + fake_stmt + post_code)
	fake_stmt_string = " ".join(fake_stmt)
	fake_class = "public class Tmp { " + fake_method + " }"
	tokens = javalang.tokenizer.tokenize(fake_class)
	parser = javalang.parser.Parser(tokens)
	root = parser.parse()
	root_node = gen_ast(root)
	unk_list = []

	current_class = "PLACEHOLDER"
	for key in global_info:
		if global_info[key]["if_current_class"]:
			current_class = key
			break
	find_unk_nodes(root_node, unk_list)
	candidate = None
	for unk_node in unk_list:
		unk_type = parse_unk_type(unk_node)
		replace_candidates = []
		if unk_type == "method_member":
			replace_method_member(unk_node, local_info, global_info, current_class, replace_candidates)
		elif unk_type == "method_qualifier":
			replace_method_qualifier(unk_node, local_info, global_info, current_class, replace_candidates, extra_global_info)
		elif unk_type == "variable_member":
			replace_variable_member(unk_node, local_info, global_info, current_class, replace_candidates)
		elif unk_type == "variable_qualifier":
			replace_variable_qualifier(unk_node, local_info, global_info, current_class, replace_candidates)

		if not replace_candidates:
			return None
		else:
			tmp_unk_index = replace_list.index([])
			replace_list[tmp_unk_index] = replace_candidates

			# term frequency
			term_frequency = {}
			for factor in replace_candidates:
				term_frequency[factor] = 0
			# for token in origin_stmt.split(" "):  # just stmt
			# for token in pre_code:  # just pre code
			# for token in post_code:  # just post code
			# for token in pre_code + origin_stmt.split(" "):  # pre + stmt
			# for token in origin_stmt.split(" ") + post_code:  # stmt + post
			for token in pre_code + origin_stmt.split(" ") + post_code:  # pre + stmt + post
				if token in term_frequency:
					term_frequency[token] += 1
			sorted_list = sorted(term_frequency.items(), key=lambda x: x[1], reverse=True)
			most_possible_candidate = sorted_list[0][0]

			# random
			# random.seed(1)
			# random.shuffle(replace_candidates)
			# most_possible_candidate = replace_candidates[0]

			unk_node.set_name(most_possible_candidate)
			fake_stmt_string = fake_stmt_string.replace("rank2fixunk", most_possible_candidate, 1)
	return [fake_stmt_string]


def replace_for_also_unk_method(pred_tgt, src_code, global_info, local_info, extra_global_info):
	fake_method = pred_tgt
	fake_method = fake_method.replace("<unk>", "rank2fixunk")
	fake_class = "public class Tmp { " + fake_method + " }"
	tokens = javalang.tokenizer.tokenize(fake_class)
	parser = javalang.parser.Parser(tokens)
	root = parser.parse()
	root_node = gen_ast(root)
	unk_list = []
	return_candidates = []

	current_class = "PLACEHOLDER"
	for key in global_info:
		if global_info[key]["if_current_class"]:
			current_class = key
			break
	find_unk_nodes(root_node, unk_list)
	for unk_node in unk_list:
		unk_type = parse_unk_type(unk_node)
		replace_candidates = []
		if unk_type == "method_member":
			replace_method_member(unk_node, local_info, global_info, current_class, replace_candidates)
		elif unk_type == "method_qualifier":
			replace_method_qualifier(unk_node, local_info, global_info, current_class, replace_candidates, extra_global_info)
		elif unk_type == "variable_member":
			replace_variable_member(unk_node, local_info, global_info, current_class, replace_candidates)
		elif unk_type == "variable_qualifier":
			replace_variable_qualifier(unk_node, local_info, global_info, current_class, replace_candidates)
		elif unk_type == "catch_type":
			replace_catch_type(replace_candidates)
		if not replace_candidates:
			return []
		else:
			# term frequency
			term_frequency = {}
			for index, factor in enumerate(replace_candidates):
				term_frequency[factor] = (0, index)
			for token in src_code.split(" "):  # pre + stmt + post
				if token in term_frequency:
					term_frequency[token] = (term_frequency[token][0]+1, term_frequency[token][1])
			sorted_list = sorted(term_frequency.items(), key=lambda x: (-x[1][0], x[1][1]))
			sorted_list = sorted_list[:10]
			# print(sorted_list)
			most_possible_candidates = [factor[0] for factor in sorted_list]
			# print("\n".join(most_possible_candidates))
			# unk_node.set_name(most_possible_candidate)
			for cand in most_possible_candidates:
				current_tgt = fake_method.replace("rank2fixunk", cand, 1)
				origin_buggy_method_tokens = [element for element in src_code.split(" ") if element != "rank2fixstart" and element != "rank2fixend"]
				pred_tokens = javalang.tokenizer.tokenize(current_tgt)
				pred_tokens = [element.value if type(element).__name__ != "String" else "\"STRING\"" for element in pred_tokens]
				if pred_tokens != origin_buggy_method_tokens:
					return_candidates.append(current_tgt)
	return return_candidates


def replace_method_member(node, var_type, class_info, current_class, replace_candidates):
	if_static = False
	qualifier_name = None
	for factor in node.parent.parent.children:
		if factor.name == "qualifier":
			qualifier_name = factor.children[0].name
	qualifier_type = None
	if qualifier_name:
		already_found = False
		for var in var_type:
			if var == qualifier_name:
				qualifier_type = var_type[var]
				already_found = True
				break
		if not already_found:
			if current_class in class_info:
				class_fields = class_info[current_class]["fields"]
				for field in class_fields:
					if field["name"] == qualifier_name:
						qualifier_type = field["type"]
						already_found = True
						break
		# if not already_found:
		# 	qualifier_type = find_field_in_super_clazz(class_info, current_class, qualifier_name)
		# 	if qualifier_type:
		# 		already_found = True
		if not already_found:
			if qualifier_name in class_info:
				qualifier_type = qualifier_name  # for static method
				if_static = True
	arg_length = 0
	arguments = []
	for factor in node.parent.parent.children:
		if factor.name == "arguments":
			arguments = factor.children
			arg_length = len(arguments)
			break
	arg_types = parse_argument_type(arguments, var_type, current_class, class_info)
	if qualifier_type:
		if qualifier_type in class_info:
			methods = class_info[qualifier_type]["methods"]
			for method in methods:
				if len(method["parameters"]) == arg_length:  # need to extend conditions
					check_flag = True
					for i in range(len(arg_types)):
						if arg_types[i] == "<unknown_type>":
							continue
						else:
							if method["parameters"][i] != arg_types[i]:
								check_flag = False
								break
					if not check_flag:
						continue
					if if_static and "static" in method["modifiers"]:
						replace_candidates.append(method["name"])
					elif not if_static and "static" not in method["modifiers"]:
						replace_candidates.append(method["name"])
	elif not qualifier_name:
		if current_class in class_info:
			methods = class_info[current_class]["methods"]
			for method in methods:  # need to extend conditions (i.g. whether args and return type are matched)
				if len(method["parameters"]) == arg_length:
					check_flag = True
					for i in range(len(arg_types)):
						if arg_types[i] == "<unknown_type>":
							continue
						else:
							if method["parameters"][i] != arg_types[i]:
								check_flag = False
								break
					if not check_flag:
						continue
					replace_candidates.append(method["name"])


def replace_method_qualifier(node, var_type, class_info, current_class, replace_candidates, extra_class_info):
	member_name = None
	method_arguments = []
	for factor in node.parent.parent.children:
		if factor.name == "member":
			member_name = factor.children[0].name
		if factor.name == "arguments":
			method_arguments = factor.children[:]
	for var in var_type:  # try in local variables
		class_type = var_type[var]
		if class_type in class_info:
			methods = class_info[class_type]["methods"]
			for method in methods:
				if method["name"] == member_name and "static" not in method["modifiers"] and len(
						method_arguments) == len(method["parameters"]):
					replace_candidates.append(var)
	if current_class in class_info:
		fields = class_info[current_class]["fields"]
		for field in fields:  # try in current class fields
			class_type = field["type"]
			if class_type in class_info:
				methods = class_info[class_type]["methods"]
				for method in methods:
					if method["name"] == member_name and "static" not in method["modifiers"] and len(
							method_arguments) == len(method["parameters"]):
						replace_candidates.append(field["name"])
		# look for fields in super class
		all_ancestor_clazz_list = []
		parse_super_class(current_class, class_info, all_ancestor_clazz_list)
		for super_clazz in all_ancestor_clazz_list:
			if super_clazz in class_info:
				fields = class_info[super_clazz]["fields"]
			elif super_clazz in extra_class_info:
				fields = extra_class_info[super_clazz]["fields"]
			else:
				continue
			for field in fields:
				class_type = field["type"]
				if class_type in class_info:
					methods = class_info[class_type]["methods"]
				elif class_type in extra_class_info:
					methods = extra_class_info[class_type]["methods"]
				else:
					continue
				for method in methods:
					if method["name"] == member_name and "static" not in method["modifiers"] and len(method_arguments) == len(method["parameters"]):
						replace_candidates.append(field["name"])
	for class_name in class_info:  # try in static class
		methods = class_info[class_name]["methods"]
		for method in methods:
			if method["name"] == member_name and "static" in method["modifiers"] and len(method_arguments) == len(
					method["parameters"]):
				replace_candidates.append(class_name)


def replace_variable_member(node, var_type, class_info, current_class, replace_candidates):
	if_static = False
	qualifier_name = None
	for factor in node.parent.parent.children:
		if factor.name == "qualifier":
			qualifier_name = factor.children[0].name
	qualifier_type = None
	if qualifier_name:
		already_found = False
		for var in var_type:
			if var == qualifier_name:
				qualifier_type = var_type[var]
				already_found = True
				break
		if not already_found:
			if current_class in class_info:
				class_fields = class_info[current_class]["fields"]
				for field in class_fields:
					if field["name"] == qualifier_name:
						qualifier_type = field["type"]
						already_found = True
						break
		if not already_found:
			if qualifier_name in class_info:
				qualifier_type = qualifier_name  # for static class
				if_static = True
	if qualifier_type:
		if qualifier_type in class_info:
			relationship = judge_class_relationship(current_class, qualifier_type, class_info)
			fields = class_info[qualifier_type]["fields"]
			for field in fields:
				if if_static and ("static" in field["modifiers"] or "default" in field["modifiers"]):
					# replace_candidates.append(field["name"])
					if relationship == "not_same_package" and "public" in field["modifiers"]:
						replace_candidates.append(field["name"])
					elif relationship == "same_package" and "private" not in field["modifiers"]:
						replace_candidates.append(field["name"])
					elif relationship == "same_class":
						replace_candidates.append(field["name"])
				elif not if_static and "static" not in field["modifiers"]:
					# replace_candidates.append(field["name"])
					if relationship == "not_same_package" and "public" in field["modifiers"]:
						replace_candidates.append(field["name"])
					elif relationship == "same_package" and "private" not in field["modifiers"]:
						replace_candidates.append(field["name"])
					elif relationship == "same_class":
						replace_candidates.append(field["name"])
	else:
		for var in var_type:
			replace_candidates.append(var)
		if current_class in class_info:
			fields = class_info[current_class]["fields"]
			for field in fields:  # need to extend conditions
				replace_candidates.append(field["name"])


def replace_variable_qualifier(node, var_type, class_info, current_class, replace_candidates):
	member_name = None
	for factor in node.parent.parent.children:
		if factor.name == "member":
			member_name = factor.children[0].name
	for var in var_type:
		class_type = var_type[var]
		if class_type in class_info:
			relationship = judge_class_relationship(current_class, class_type, class_info)
			fields = class_info[class_type]["fields"]
			for field in fields:
				if field["name"] == member_name and "static" not in field["modifiers"]:
					if relationship == "not_same_package" and "public" in field["modifiers"]:
						replace_candidates.append(var)
					elif relationship == "same_package" and "private" not in field["modifiers"]:
						replace_candidates.append(var)
					elif relationship == "same_class":
						replace_candidates.append(var)
	if current_class in class_info:
		for field in class_info[current_class]["fields"]:  # try in current class fields
			class_type = field["type"]
			if class_type in class_info:
				relationship = judge_class_relationship(current_class, class_type, class_info)
				fields = class_info[class_type]["fields"]
				for field in fields:
					# replace_candidates.append(field["name"])
					if field["name"] == member_name and "static" not in field["modifiers"]:
						if relationship == "not_same_package" and "public" in field["modifiers"]:
							replace_candidates.append(field["name"])
						elif relationship == "same_package" and "private" not in field["modifiers"]:
							replace_candidates.append(field["name"])
						elif relationship == "same_class":
							replace_candidates.append(field["name"])
	for class_name in class_info:  # try in static class
		relationship = judge_class_relationship(current_class, class_name, class_info)
		fields = class_info[class_name]["fields"]
		for field in fields:
			if field["name"] == member_name and "static" in field["modifiers"]:
				# replace_candidates.append(class_name)
				if relationship == "not_same_package" and "public" in field["modifiers"]:
					replace_candidates.append(class_name)
				elif relationship == "same_package" and "private" not in field["modifiers"]:
					replace_candidates.append(class_name)
				elif relationship == "same_class":
					replace_candidates.append(class_name)


def replace_variable_dec_name():
	pass


def replace_method_dec_name():
	pass


def replace_type_name():
	pass


def replace_return_type():
	pass


def replace_parameter_name():
	pass


def replace_constructor_dec_name():
	pass



def replace_unk(node, unk_type, var_type, class_info, src_code):  # to be continued
	current_class = "PLACEHOLDER"
	for key in class_info:
		if class_info[key]["if_current_class"]:
			current_class = key
			break
	replace_candidates = []

	multi_unk_flag = False

	# variable_dec_name
	if unk_type == "variable_dec_name":
		# parent = node.parent
		# while parent.name != "MethodDeclaration":
		# 	parent = parent.parent
		# 	if not parent:
		# 		break
		# used_variable_list = []
		# get_all_used_variable(parent, used_variable_list, node.position[1], class_info)
		# used_variable_list = set(used_variable_list)
		#
		# defined_variable_list = []
		# get_all_def_variable(parent, defined_variable_list)
		# defined_variable_list = set(defined_variable_list)
		#
		# for var in used_variable_list:
		# 	if var not in defined_variable_list:
		# 		replace_candidates.append(var)

		src_code = src_code.split(" ")
		start_index = src_code.index("rank2fixstart")
		end_index = src_code.index("rank2fixend")
		fault_code_token_list = src_code[start_index + 1: end_index]
		src_code = " ".join(src_code).replace("rank2fixstart", "").replace("rank2fixend", "")
		fake_code = "public class Tmp { " + src_code + " }"
		try:
			tokens = javalang.tokenizer.tokenize(fake_code)
			parser = javalang.parser.Parser(tokens)
			root = parser.parse()
			root_node = gen_ast(root)
			var_list = []
			find_variable_decl_names(root_node, var_list)
			for factor in var_list:
				if factor in fault_code_token_list:
					replace_candidates.append(factor)
		except:
			pass

	# method_dec_name
	elif unk_type == "method_dec_name":
		src_code = src_code.replace("rank2fixstart", "").replace("rank2fixend", "")
		fake_code = "public class Tmp { " + src_code + " }"
		try:
			tokens = javalang.tokenizer.tokenize(fake_code)
			parser = javalang.parser.Parser(tokens)
			root = parser.parse()
			root_node = gen_ast(root)
			method_name = find_method_decl_name(root_node)
			if method_name:
				replace_candidates.append(method_name)
		except:
			pass

	# type_name
	elif unk_type == "type_name":
		src_code = src_code.split(" ")
		start_index = src_code.index("rank2fixstart")
		end_index = src_code.index("rank2fixend")
		fault_code_token_list = src_code[start_index + 1: end_index]
		src_code = " ".join(src_code).replace("rank2fixstart", "").replace("rank2fixend", "")
		fake_code = "public class Tmp { " + src_code + " }"
		try:
			tokens = javalang.tokenizer.tokenize(fake_code)
			parser = javalang.parser.Parser(tokens)
			root = parser.parse()
			root_node = gen_ast(root)
			type_list = []
			find_type_names(root_node, type_list)
			type_list = set(type_list)
			for factor in type_list:
				if factor in fault_code_token_list:
					replace_candidates.append(factor)
		except:
			pass

	# return_type
	elif unk_type == "return_type":
		src_code = src_code.replace("rank2fixstart", "").replace("rank2fixend", "")
		fake_code = "public class Tmp { " + src_code + " }"
		try:
			tokens = javalang.tokenizer.tokenize(fake_code)
			parser = javalang.parser.Parser(tokens)
			root = parser.parse()
			root_node = gen_ast(root)
			return_type = find_return_type(root_node)
			if return_type:
				replace_candidates.append(return_type)
		except:
			pass

	# parameter_name
	elif unk_type == "parameter_name":
		src_code = src_code.replace("rank2fixstart", "").replace("rank2fixend", "")
		fake_code = "public class Tmp { " + src_code + " }"
		try:
			tokens = javalang.tokenizer.tokenize(fake_code)
			parser = javalang.parser.Parser(tokens)
			root = parser.parse()
			root_node = gen_ast(root)
			param_list = []
			find_parameter_names(root_node, param_list)
			parent = node.parent
			curr_param_index = 0
			while parent and parent.name != "FormalParameter":
				parent = parent.parent
			if parent:
				curr_param_index = parent.parent.children.index(parent)
			if curr_param_index < len(param_list):
				replace_candidates.append(param_list[curr_param_index])
		except:
			pass

	# constructor_dec_name
	elif unk_type == "constructor_dec_name":
		src_code = src_code.replace("rank2fixstart", "").replace("rank2fixend", "")
		fake_code = "public class Tmp { " + src_code + " }"
		try:
			tokens = javalang.tokenizer.tokenize(fake_code)
			parser = javalang.parser.Parser(tokens)
			root = parser.parse()
			root_node = gen_ast(root)
			constructor_name = find_constructor_decl_name(root_node)
			if constructor_name:
				replace_candidates.append(constructor_name)
		except:
			pass

	return replace_candidates, multi_unk_flag
