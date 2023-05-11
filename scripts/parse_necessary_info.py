import os
import javalang
import sys
import pickle
import collections


def cut_data(token_seq, token_length_for_reserve):
	if len(token_seq) <= token_length_for_reserve:
		return token_seq
	else:
		start_index = token_seq.index("rank2fixstart")
		end_index = token_seq.index("rank2fixend")
		assert end_index > start_index
		length_of_annotated_statement = end_index - start_index + 1
		if length_of_annotated_statement <= token_length_for_reserve:
			padding_length = token_length_for_reserve - length_of_annotated_statement
			# give 2/3 padding space to content before annotated statement
			pre_padding_length = padding_length // 3 * 2
			# give 1/3 padding space to content after annotated statement
			post_padding_length = padding_length - pre_padding_length
			if start_index >= pre_padding_length and len(token_seq) - end_index - 1 >= post_padding_length:
				return token_seq[start_index - pre_padding_length: end_index + 1 + post_padding_length]
			elif start_index < pre_padding_length:
				return token_seq[:token_length_for_reserve]
			elif len(token_seq) - end_index - 1 < post_padding_length:
				return token_seq[len(token_seq) - token_length_for_reserve:]
		else:
			return token_seq[start_index: start_index + token_length_for_reserve]


def parse_clazz(file_path, clazz_info, if_current_class, super_clazz_list):
	try:
		with open(file_path, "r", encoding="utf-8") as file:
			code = file.read()
	except UnicodeDecodeError:
		with open(file_path, "r", encoding="latin1") as file:
			code = file.read()
	try:
		tokens = javalang.tokenizer.tokenize(code)
		parser = javalang.parser.Parser(tokens)
		root = parser.parse()
	except javalang.parser.JavaSyntaxError:
		return False

	# get package
	clazz_package = root.package
	if clazz_package:
		clazz_package = clazz_package.name
	else:
		clazz_package = ""
	for clazz in root.types:
		parse_clazz_elements(clazz_package, clazz, clazz_info, if_current_class, super_clazz_list)
	return True


def parse_clazz_elements(clazz_package, clazz, clazz_info, if_current_class, super_clazz_list):
	# get class name
	clazz_name = clazz.name

	# get modifiers
	clazz_modifiers = clazz.modifiers

	# get fields
	clazz_fields = []
	if type(clazz).__name__ == "ClassDeclaration":
		fields = clazz.fields
		for field in fields:
			field_modifiers = field.modifiers
			field_type = field.type.name + "[]" * len(field.type.dimensions)
			for factor in field.declarators:
				field_name = factor.name
				clazz_fields.append({"name": field_name, "type": field_type, "modifiers": field_modifiers})
	
	elif type(clazz).__name__ == "EnumDeclaration":
		constants = clazz.body.constants
		for constant in constants:
			const_name = constant.name
			const_type = clazz_name
			clazz_fields.append({"name": const_name, "type": const_type, "modifiers": "default"})

	# get methods:
	methods = clazz.methods
	clazz_methods = []
	for method in methods:
		method_modifiers = method.modifiers
		method_name = method.name
		if method.return_type:
			method_return_type = method.return_type.name + "[]" * len(method.return_type.dimensions)
		else:
			method_return_type = "void"
		param_type_list = []
		for param in method.parameters:
			param_type_list.append(param.type.name + "[]" * len(param.type.dimensions))
		method_params = param_type_list
		clazz_methods.append({"name": method_name, "type": method_return_type, "parameters": method_params, "modifiers": method_modifiers})

	# get super class:
	super_clazz_names = []
	if type(clazz).__name__ == "InterfaceDeclaration":
		if clazz.extends:
			for super_clazz in clazz.extends:
				super_clazz_names.append(super_clazz.name)
	elif type(clazz).__name__ == "ClassDeclaration":
		if clazz.extends:
			super_clazz_names.append(clazz.extends.name)

	# get implements
	implement_names = []
	if type(clazz).__name__ == "EnumDeclaration" or type(clazz).__name__ == "ClassDeclaration":
		if clazz.implements:
			for implement in clazz.implements:
				implement_names.append(implement.name)

	# generate clazz info dictionary
	if if_current_class or clazz_name not in clazz_info:
		clazz_info[clazz_name] = {"package": clazz_package, "modifiers": clazz_modifiers, "fields": clazz_fields,
								  "methods": clazz_methods, "super_class": super_clazz_names,
								  "implements": implement_names, "if_current_class": if_current_class}
	super_clazz_list += super_clazz_names

	# for inner class
	for factor in clazz.body:
		if type(factor).__name__ == "ClassDeclaration" or type(factor).__name__ == "EnumDeclaration":
			parse_clazz_elements(clazz_package, factor, clazz_info, False, super_clazz_list)


def get_local_info(node, end_pos, local_info, start_pos):
	if node:
		if type(node) == list:
			for factor in node:
				get_local_info(factor, end_pos, local_info, start_pos)
		elif type(node) == str:
			return
		elif type(node) == set:
			return
		elif type(node) == bool:
			return
		else:
			if node.position:
				start_pos = node.position[0]
			if type(node).__name__ == "MethodDeclaration" or type(node).__name__ == "ConstructorDeclaration":
				parameters = node.parameters
				for param in parameters:
					array_dim = len(param.type.dimensions)
					if array_dim == 0:
						local_info[param.name] = param.type.name
					else:
						local_info[param.name] = param.type.name + "[]" * len(param.type.dimensions)
						local_info[param.name + "[]" * array_dim] = param.type.name
			elif type(node).__name__ == "LocalVariableDeclaration" or type(node).__name__ == "VariableDeclaration":
				if start_pos > end_pos:
					return
				class_type = node.type.name
				array_dim = len(node.type.dimensions)
				for declarator in node.declarators:
					local_info[declarator.name] = class_type + "[]" * len(node.type.dimensions)
					local_info[declarator.name + "[]" * array_dim] = node.type.name
			elif type(node).__name__ == "CatchClauseParameter":
				if start_pos > end_pos:
					return
				class_type = node.types[0]
				local_info[node.name] = class_type
			if node.children:
				for child in node.children:
					get_local_info(child, end_pos, local_info, start_pos)


def get_global_info(file_path, clazz_info, extra_clazz_info, all_clazz_paths, jdk_and_external_paths, already_parsed_paths, is_extra, already_used_super_clazz):
	try:
		with open(file_path, "r", encoding="utf-8") as file:
			code = file.read()
	except UnicodeDecodeError:
		with open(file_path, "r", encoding="latin1") as file:
			code = file.read()
	try:
		tokens = javalang.tokenizer.tokenize(code)
		parser = javalang.parser.Parser(tokens)
		root = parser.parse()
	except javalang.parser.JavaSyntaxError:
		print("Syntax errors occur while trying to get global info")
		return 

	# get package
	clazz_package = root.package
	if clazz_package:
		clazz_package = clazz_package.name
		package_path_length = clazz_package.split(".")
	else:
		clazz_package = ""
		package_path_length = []

	# get project src dir
	project_src_path = "/".join(file_path.split("/")[: -(len(package_path_length) + 1)])
	test_flag = False
	if "/test/" in project_src_path:
		test_flag = True

	# get imports and parse imported class
	imports = root.imports
	for current_import in imports:
		find_flag = False
		import_path = current_import.path
		import_wildcard = current_import.wildcard
		if not import_wildcard:
			package_elements = import_path.split(".")
			inner_elements = []
			path_elements = []
			clazz_flag = True
			for factor in package_elements:
				if not clazz_flag:
					inner_elements.append(factor)
				elif factor[0].islower():
					path_elements.append(factor)
				else:
					path_elements.append(factor)
					clazz_flag = False
			import_clazz_file_path = os.path.join(project_src_path, ".".join(path_elements).replace(".", "/") + ".java")
			if not test_flag and os.path.exists(import_clazz_file_path):
				find_flag = True
				if import_clazz_file_path in already_parsed_paths:
					continue
				if is_extra:
					status = parse_clazz(import_clazz_file_path, extra_clazz_info, False, [])
				else:
					status = parse_clazz(import_clazz_file_path, clazz_info, False, [])
				if not status:
					print("Global info: Syntax errors occur while parsing class file {}".format(
						import_clazz_file_path))
				already_parsed_paths.append(import_clazz_file_path)
			else:
				for path in all_clazz_paths + jdk_and_external_paths:
					if path[:-5].replace("/", ".").endswith(import_path):
						if "/test/" in path:
							continue
						find_flag = True
						if path in already_parsed_paths:
							continue
						if is_extra:
							status = parse_clazz(path, extra_clazz_info, False, [])
						else:
							status = parse_clazz(path, clazz_info, False, [])
						if not status:
							print("Global info: Syntax errors occur while parsing class file {}".format(path))
						already_parsed_paths.append(path)
						break
		else:
			import_parent_dir = os.path.join(project_src_path, import_path.replace(".", "/"))
			if not test_flag and os.path.exists(import_parent_dir):
				find_flag = True
				for tmp_clazz_name in os.listdir(import_parent_dir):
					absolute_clazz_path = os.path.join(import_parent_dir, tmp_clazz_name)
					if absolute_clazz_path in already_parsed_paths:
						continue
					if not os.path.isfile(absolute_clazz_path):
						continue
					if not absolute_clazz_path.endswith(".java"):
						continue
					if is_extra:
						status = parse_clazz(absolute_clazz_path, extra_clazz_info, False, [])
					else:
						status = parse_clazz(absolute_clazz_path, clazz_info, False, [])
					if not status:
						print("Global info: Syntax errors occur while parsing class file {}".format(absolute_clazz_path))
					already_parsed_paths.append(absolute_clazz_path)
			else:
				required_pacakge_path = None
				for path in all_clazz_paths + jdk_and_external_paths:
					absolute_package = ".".join(path[:-5].replace("/", ".").split(".")[:-1])
					if absolute_package.endswith(import_path):
						if ".test." in absolute_package:
							continue
						find_flag = True
						required_pacakge_path = "/".join(path.split("/")[:-1])
						break
				if required_pacakge_path:
					for file_name in os.listdir(required_pacakge_path):
						current_file_path = os.path.join(required_pacakge_path, file_name)
						if current_file_path in already_parsed_paths:
							continue
						if not os.path.isfile(current_file_path):
							continue
						if not current_file_path.endswith(".java"):
							continue
						if is_extra:
							status = parse_clazz(current_file_path, extra_clazz_info, False, [])
						else:
							status = parse_clazz(current_file_path, clazz_info, False, [])
						if not status:
							print("Global info: Syntax errors occur while parsing class file {}".format(current_file_path))
						already_parsed_paths.append(current_file_path)

	# parse the classes in the same package
	for path in all_clazz_paths:
		if "/test/" in path:
			continue
		if ".".join(path.split("/")[:-1]).endswith(clazz_package):
			new_file_path = path
			if not os.path.isfile(new_file_path):
				continue
			if not new_file_path.endswith(".java"):
				continue
			if new_file_path in already_parsed_paths:
				continue
			if is_extra:
				status = parse_clazz(new_file_path, extra_clazz_info, False, [])
			else:
				status = parse_clazz(new_file_path, clazz_info, False, [])
			if not status:
				print("Global info: Syntax errors occur while parsing class file {}".format(new_file_path))

	# parse the class it self
	super_clazz_list = []
	if is_extra:
		status = parse_clazz(file_path, extra_clazz_info, False, super_clazz_list)
	else:
		status = parse_clazz(file_path, clazz_info, True, super_clazz_list)
	if not status:
		print("Global info: Syntax errors occur while parsing class file {}".format(file_path))
	for super_clazz in super_clazz_list:
		if super_clazz in already_used_super_clazz:
			continue
		already_used_super_clazz.append(super_clazz)
		flag = False
		for file_path in already_parsed_paths:
			if file_path[:-5].split("/")[-1] == super_clazz:
				get_global_info(file_path, clazz_info, extra_clazz_info, all_clazz_paths, jdk_and_external_paths, already_parsed_paths, True, already_used_super_clazz)
				flag = True
				break
		if not flag:
			for file_path in all_clazz_paths:
				if file_path[:-5].split("/")[-1] == super_clazz:
					get_global_info(file_path, clazz_info, extra_clazz_info, all_clazz_paths, jdk_and_external_paths, already_parsed_paths, True, already_used_super_clazz)
					break


def main():
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]

	parsed_data_dir = "../parsed_data/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version)
	anno_file_path = os.path.join(parsed_data_dir, "fl_no_empty.txt")
	method_data_dir = os.path.join(parsed_data_dir, "data_no_empty/")
	src_path_path = "../necessary_info/d4j_{}/src_path.txt".format(d4j_version)
	project_path = "../projects/d4j_{}/{}/".format(d4j_version, bug_version)
	src_path = os.path.join(parsed_data_dir, "src_no_cut.txt")
	output_dir = os.path.join(parsed_data_dir, "completion_info/")
	jdk_path = "../necessary_info/d4j_{}/JDK_{}/".format(d4j_version, "1.7" if d4j_version == "v1" else "1.8")
	third_party_path = "../necessary_info/d4j_{}/third_party/".format(d4j_version)
	token_length_for_reserve = 500

	if not os.path.exists(output_dir):
		os.makedirs(output_dir)

	with open(anno_file_path, "r", encoding="utf-8") as file:
		annos = file.readlines()
		annos = [factor.strip() for factor in annos]

	with open(src_path_path, "r", encoding="utf-8") as file:
		version_info = collections.OrderedDict()
		for line in file.readlines():
			line = line.strip()
			version_info[line.split(":")[0]] = line.split(":")[1]

	cmd = "cd {} && find . -type f -name \"*.java\"".format(jdk_path)
	results = os.popen(cmd).readlines()
	jdk_paths = [os.path.join(jdk_path, factor.strip()[2:]) for factor in results]
	
	# parse data
	global_info = []
	extra_global_info = []
	local_info = []
	corresponding_buggy_file = []

	with open(os.path.join(output_dir, "src.txt"), "w", encoding="utf-8") as output_src_file:
		with open(os.path.join(output_dir, "sample_info.txt"), "w", encoding="utf-8") as sample_info_file:
			# for src no cut
			with open(src_path, "r", encoding="utf-8") as file:
				srcs = file.readlines()
				srcs = [factor.strip() for factor in srcs]
				
			for index, anno in enumerate(annos):
				print(index + 1)

				# for src cut
				tokens = srcs[index].split(" ")
				tokens = cut_data(tokens, token_length_for_reserve)
				output_src_file.write(" ".join(tokens))
				output_src_file.write("\n")
				
				# for local_info
				end_pos = -1
				with open(os.path.join(method_data_dir, "{}.txt".format(index + 1)), "r") as file:
					method = file.readlines()
				for line_index, line in enumerate(method):
					if "rank2fixstart" in line:
						end_pos = line_index + 2  # because later add a previous line to combine a fake class
						break
				assert end_pos != -1

				content = "public class Tmp {\n" + "".join(method) + "\n}"
				content = content.replace("rank2fixstart", "").replace("rank2fixend", "")
				current_local_info = collections.OrderedDict()
				root = None
				try:
					tokens = javalang.tokenizer.tokenize(content)
					parser = javalang.parser.Parser(tokens)
					root = parser.parse()
				except:
					print("Local info: Syntax errors occur")
				if root:
					get_local_info(root, end_pos, current_local_info, -1)

				local_info.append(current_local_info)

				# for global_info and extra_global_info
				package_name = anno.split("@")[0]
				buggy_file_path = os.path.join(project_path, version_info[bug_version], package_name.replace(".", "/") + ".java")
			
				project_root_dir = project_path
				cmd = "cd {} && find . -type f -name \"*.java\"".format(project_root_dir)
				results = os.popen(cmd).readlines()
				clazz_info = collections.OrderedDict()
				extra_clazz_info = collections.OrderedDict()
				already_parsed_paths = []
				all_clazz_paths = [os.path.join(project_root_dir, factor.strip()[2:]) for factor in results]

				cmd = "cd {} && find . -type f -name \"*.java\"".format(os.path.join(third_party_path, bug_version))
				results = os.popen(cmd).readlines()
				external_paths = [os.path.join(third_party_path, bug_version, factor.strip()[2:]) for factor in results]
				jdk_and_external_paths = external_paths + jdk_paths

				already_used_super_clazz = []
				get_global_info(buggy_file_path, clazz_info, extra_clazz_info, all_clazz_paths, jdk_and_external_paths, already_parsed_paths, False, already_used_super_clazz)
				global_info.append(clazz_info)
				extra_global_info.append(extra_clazz_info)
	
				# for the corresponding buggy file
				try:
					with open(buggy_file_path, "r", encoding="utf-8") as file:
						code = file.read()
				except UnicodeDecodeError:
					with open(buggy_file_path, "r", encoding="latin1") as file:
						code = file.read()	
				corresponding_buggy_file.append(code)
				
				# for buggy info
				abs_buggy_file_path = os.path.abspath(buggy_file_path)
				sample_info_file.write("{},{}\n".format(bug_version, abs_buggy_file_path))

	with open(os.path.join(output_dir, "local_info.pkl"), "wb") as pickle_file:
		pickle.dump(local_info, pickle_file)
	with open(os.path.join(output_dir, "global_info.pkl"), "wb") as pickle_file:
		pickle.dump(global_info, pickle_file)
	with open(os.path.join(output_dir, "extra_global_info.pkl"), "wb") as pickle_file:
		pickle.dump(extra_global_info, pickle_file)
	with open(os.path.join(output_dir, "buggy_file.pkl"), "wb") as pickle_file:
		pickle.dump(corresponding_buggy_file, pickle_file)
	

if __name__ == "__main__":
	main()
