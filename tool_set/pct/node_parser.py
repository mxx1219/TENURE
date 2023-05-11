import javalang
import os


def parse_ast(node, search_list, is_selector):
	if not node:
		return
	elif type(node).__name__ == "list":
		for factor in node:
			parse_ast(factor, search_list, is_selector)
		return 
	elif type(node).__name__ == "set":
		for factor in node:
			parse_ast(factor, search_list, is_selector)
		return
	elif type(node).__name__ == "str":
		return
	elif type(node).__name__ == "bool":
		return
	else:
		if not is_selector:
			if type(node).__name__ == "MethodInvocation":
				search_list.append(node)
			elif type(node).__name__ == "MemberReference":
				search_list.append(node)
			elif type(node).__name__ == "ReferenceType":
				search_list.append(node)
			elif type(node).__name__ == "This":
				search_list.append(node)
			elif type(node).__name__ == "SuperMemberReference":
				search_list.append(node)
			elif type(node).__name__ == "SuperMethodInvocation":
				search_list.append(node)
			elif type(node).__name__ == "CatchClauseParameter":
				for catch_type in node.types:
					search_list.append(catch_type)
				return
			elif type(node).__name__ == "MethodDeclaration" and node.throws:
				for exception in node.throws:
					search_list.append(exception)

		filtered_indices = []
		if "selectors" in node.attrs:
			filtered_indices.append(node.attrs.index("selectors"))
		elif "sub_type" in node.attrs:
			filtered_indices.append(node.attrs.index("sub_type"))

		for i, child in enumerate(node.children):
			if i not in filtered_indices:
				parse_ast(child, search_list, False)
			else:
				parse_ast(child, search_list, True)


def parse_method_invocation(node):
	if node.qualifier:
		out = "{}.{}({})".format(node.qualifier, node.member, len(node.arguments))
	else:
		out = "{}({})".format(node.member, len(node.arguments))
	if node.selectors:
		for factor in node.selectors:
			child_out = None
			if type(factor).__name__ == "MethodInvocation":
				child_out = parse_method_invocation(factor)
			elif type(factor).__name__ == "MemberReference":
				child_out = parse_member_reference(factor)
			elif type(factor).__name__ == "ArraySelector":
				child_out = "[]"
			if child_out:
				if child_out == "[]":
					out = "{}{}".format(out, child_out)
				else:
					out = "{}.{}".format(out, child_out)
	return out


def parse_member_reference(node):
	if node.qualifier:
		out = "{}.{}".format(node.qualifier, node.member)
	else:
		out = node.member
	if node.selectors:
		for factor in node.selectors:
			child_out = None
			if type(factor).__name__ == "MethodInvocation":
				child_out = parse_method_invocation(factor)
			elif type(factor).__name__ == "MemberReference":
				child_out = parse_member_reference(factor)
			elif type(factor).__name__ == "ArraySelector":
				child_out = "[]"
			if child_out:
				if child_out == "[]":
					out = "{}{}".format(out, child_out)
				else:
					out = "{}.{}".format(out, child_out)
	return out


def parse_reference_type(node):
	out = node.name
	if node.sub_type:
		if type(node.sub_type).__name__ == "ReferenceType":
			child_out = parse_reference_type(node.sub_type)
			out = "{}.{}".format(node.name, child_out)
	return out


def parse_this(node):
	if node.qualifier:
		out = "{}.this".format(node.qualifier)
	else:
		out = "this"
	if node.selectors:
		for factor in node.selectors:
			child_out = None
			if type(factor).__name__ == "MethodInvocation":
				child_out = parse_method_invocation(factor)
			elif type(factor).__name__ == "MemberReference":
				child_out = parse_member_reference(factor)
			elif type(factor).__name__ == "ArraySelector":
				child_out = "[]"
			if child_out:
				if child_out == "[]":
					out = "{}{}".format(out, child_out)
				else:
					out = "{}.{}".format(out, child_out)
	return out


def parse_super_member_reference(node):
	if node.qualifier:
		out = "{}.super.{}".format(node.qualifier, node.member)
	else:
		out = "super.{}".format(node.member)
	if node.selectors:
		for factor in node.selectors:
			child_out = None
			if type(factor).__name__ == "MethodInvocation":
				child_out = parse_method_invocation(factor)
			elif type(factor).__name__ == "MemberReference":
				child_out = parse_member_reference(factor)
			elif type(factor).__name__ == "ArraySelector":
				child_out = "[]"
			if child_out:
				if child_out == "[]":
					out = "{}{}".format(out, child_out)
				else:
					out = "{}.{}".format(out, child_out)
	return out


def parse_super_method_invocation(node):
	if node.qualifier:
		out = "{}.super.{}({})".format(node.qualifier, node.member, len(node.arguments))
	else:
		out = "super.{}({})".format(node.member, len(node.arguments))
	if node.selectors:
		for factor in node.selectors:
			child_out = None
			if type(factor).__name__ == "MethodInvocation":
				child_out = parse_method_invocation(factor)
			elif type(factor).__name__ == "MemberReference":
				child_out = parse_member_reference(factor)
			elif type(factor).__name__ == "ArraySelector":
				child_out = "[]"
			if child_out:
				if child_out == "[]":
					out = "{}{}".format(out, child_out)
				else:
					out = "{}.{}".format(out, child_out)
	return out


def get_expr(content, whole_content):
	# content = "public class Tmp { \n" + content + "\n}"
	syntax_correct_content = content
	try:
		tokens = javalang.tokenizer.tokenize(content)
		parser = javalang.parser.Parser(tokens)
		root = parser.parse()
	except:
		if content == whole_content:
			return [], False
		else:
			try:
				fake_clazz = "public class Tmp {\n" + whole_content + "\n}"
				tokens = javalang.tokenizer.tokenize(fake_clazz)
				parser = javalang.parser.Parser(tokens)
				root = parser.parse()
				syntax_correct_content = fake_clazz
			except:
				return [], False
	search_list = []
	parse_ast(root, search_list, False)
	string_list = []
	final_list = []
	for factor in search_list:
		if str(factor) not in string_list:
			string_list.append(str(factor))
			final_list.append(factor)
	results = []
	for factor in final_list:
		if type(factor).__name__ == "MethodInvocation":
			out = parse_method_invocation(factor)
		elif type(factor).__name__ == "MemberReference":
			out = parse_member_reference(factor)
		elif type(factor).__name__ == "ReferenceType":
			out = parse_reference_type(factor)
		elif type(factor).__name__ == "This":
			out = parse_this(factor)
		elif type(factor).__name__ == "SuperMemberReference":
			out = parse_super_member_reference(factor)
		elif type(factor).__name__ == "SuperMethodInvocation":
			out = parse_super_method_invocation(factor)
		elif type(factor).__name__ == "str":
			out = factor
		else:
			out = None
		if out:
			if out not in results:
				results.append(out)
	return results, True, syntax_correct_content


def parse_specific_node(node):
	search_list = []
	parse_ast(node, search_list, False)
	string_list = []
	final_list = []
	for factor in search_list:
		if str(factor) not in string_list:
			string_list.append(str(factor))
			final_list.append(factor)
	results = []
	for factor in final_list:
		if type(factor).__name__ == "MethodInvocation":
			out = parse_method_invocation(factor)
		elif type(factor).__name__ == "MemberReference":
			out = parse_member_reference(factor)
		elif type(factor).__name__ == "ReferenceType":
			out = parse_reference_type(factor)
		elif type(factor).__name__ == "This":
			out = parse_this(factor)
		elif type(factor).__name__ == "SuperMemberReference":
			out = parse_super_member_reference(factor)
		elif type(factor).__name__ == "SuperMethodInvocation":
			out = parse_super_method_invocation(factor)
		elif type(factor).__name__ == "str":
			out = factor
		else:
			out = None
		if out:
			if out not in results:
				results.append(out)
	return results, True

