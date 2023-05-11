import os
import javalang
import pickle
import sys


def parse_clazz_declaration(clazz, clazz_info, clazz_package, clazz_imports, external_clazzes, external_fields, external_methods):
	# get class name
	clazz_name = clazz.name

	# get modifiers
	clazz_modifiers = clazz.modifiers

	# get fields
	fields = clazz.fields
	clazz_fields = []
	for field in fields:
		field_modifiers = field.modifiers
		field_type = field.type.name
		array_dim = len(field.type.dimensions)
		if array_dim == 0:
			for factor in field.declarators:
				field_name = factor.name
				clazz_fields.append({"name": field_name, "type": field_type, "modifiers": field_modifiers})
		else:
			for factor in field.declarators:
				field_name = factor.name + "[]" * array_dim
				clazz_fields.append({"name": field_name, "type": field_type, "modifiers": field_modifiers})
				field_name = factor.name
				clazz_fields.append(
					{"name": field_name, "type": field_type + "[]" * array_dim, "modifiers": field_modifiers})
	# for inner class
	clazz_fields += external_fields

	# enum type is a little special
	if type(clazz).__name__ == "EnumDeclaration":
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
			method_return_type = method.return_type.name
			array_dim = len(method.return_type.dimensions)
			method_return_type += "[]" * array_dim
		else:
			method_return_type = "void"
		param_type_list = []
		for param in method.parameters:
			if type(param.type).__name__ == "BasicType":
				complete_type = param.type.name
			else:
				complete_type = param.type.name
				sub_type = param.type.sub_type
				while sub_type:
					complete_type += ".{}".format(sub_type.name)
					sub_type = sub_type.sub_type
			param_type_list.append(complete_type.split(".")[-1] + "[]" * len(param.type.dimensions))
		method_params = param_type_list
		clazz_methods.append({"name": method_name, "type": method_return_type, "parameters": method_params,
							  "modifiers": method_modifiers})
	# for inner class
	clazz_methods += external_methods

	# get super class:
	super_clazz_names = []
	if type(clazz).__name__ == "InterfaceDeclaration":
		if clazz.extends:
			for super_clazz in clazz.extends:
				super_clazz_names.append(super_clazz.name)
	elif type(clazz).__name__ == "ClassDeclaration":
		if clazz.extends:
			actual_clazz_name = clazz.extends.name
			subtype = clazz.extends.sub_type
			while subtype:
				actual_clazz_name += ".{}".format(subtype.name)
				subtype = subtype.sub_type
			super_clazz_names.append(actual_clazz_name)
	# for enum type, the default super class is java.lang.Enum
	elif type(clazz).__name__ == "EnumDeclaration":
		super_clazz_names.append("Enum")

	# get implements
	implement_names = []
	if type(clazz).__name__ == "EnumDeclaration" or type(clazz).__name__ == "ClassDeclaration":
		if clazz.implements:
			for implement in clazz.implements:
				implement_names.append(implement.name)

	# generate clazz info dictionary
	if clazz_name not in clazz_info:
		clazz_info[clazz_name] = []
	clazz_info[clazz_name].append(
		{"name": clazz_name, "package": clazz_package, "modifiers": clazz_modifiers, "fields": clazz_fields,
		 "methods": clazz_methods, "super_class": super_clazz_names, "implements": implement_names,
		 "imports": clazz_imports, "external_clazzes": external_clazzes})

	# for inner class
	for child in clazz.body:
		if type(child).__name__ == "ClassDeclaration" or type(child).__name__ == "InterfaceDeclaration" or \
				type(child).__name__ == "EnumDeclaration":
			external_clazzes_after_combine = external_clazzes + [clazz.name]
			# inner class can invoke its external classes
			external_fields = clazz_info[clazz_name][-1]["fields"][:]
			external_methods = clazz_info[clazz_name][-1]["methods"][:]
			parse_clazz_declaration(child, clazz_info, clazz_package, clazz_imports, external_clazzes_after_combine, external_fields, external_methods)


def parse_clazz_type(file_path, clazz_info):
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
		return

	# get package
	clazz_package = root.package
	if clazz_package:
		clazz_package = clazz_package.name
	else:
		clazz_package = ""

	# get imports
	clazz_imports = []
	import_list = root.imports
	for factor in import_list:
		path = factor.path
		if_static = factor.static
		if_wildcard = factor.wildcard
		clazz_imports.append({"path": path, "if_static": if_static, "if_wildcard": if_wildcard})
	# add java.lang (default added)
	clazz_imports.append({"path": "java.lang", "if_static": False, "if_wildcard": True})
	# add same package classes
	clazz_imports.append({"path": clazz_package, "if_static": False, "if_wildcard": True})

	for clazz in root.types:
		parse_clazz_declaration(clazz, clazz_info, clazz_package, clazz_imports, [], [], [])


def main():
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]

	src_path_path = "../necessary_info/d4j_{}/src_path.txt".format(d4j_version)
	project_path = "../projects/d4j_{}/{}/".format(d4j_version, bug_version)
	output_dir = "../parsed_data/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version)
	jdk_path = "../necessary_info/d4j_{}/JDK_{}/".format(d4j_version, "1.7" if d4j_version == "v1" else "1.8")
	third_party_path = "../necessary_info/d4j_{}/third_party/".format(d4j_version)

	with open(src_path_path, "r", encoding="utf-8") as file:
		version_info = {}
		for line in file.readlines():
			line = line.strip()
			version_info[line.split(":")[0]] = line.split(":")[1]

		# initialize
		jdk_class_info = {}

		# jdk paths
		print("parse jdk ...")
		cmd = "cd {} && find . -type f -name \"*.java\"".format(jdk_path)
		results = os.popen(cmd).readlines()
		jdk_paths = [os.path.join(jdk_path, factor.strip()[2:]) for factor in results]
		print("num: {}".format(len(jdk_paths)))
		for path in jdk_paths:
			parse_clazz_type(path, jdk_class_info)
		with open(os.path.join(output_dir, "jdk_info.pkl"), "wb") as file:
			pickle.dump(jdk_class_info, file)

		print("parse project ...")
		# initialize
		pro_class_info = {}

		# src paths
		src_path = os.path.join(project_path, version_info[bug_version])
		cmd = "cd {} && find . -type f -name \"*.java\"".format(src_path)
		results = os.popen(cmd).readlines()
		src_paths = [os.path.join(src_path, factor.strip()[2:]) for factor in results]
		print("num: {}".format(len(src_paths)))
		for path in src_paths:
			parse_clazz_type(path, pro_class_info)

		# jar paths
		jar_path = os.path.join(third_party_path, bug_version)
		cmd = "cd {} && find . -type f -name \"*.java\"".format(jar_path)
		results = os.popen(cmd).readlines()
		jar_paths = [os.path.join(jar_path, factor.strip()[2:]) for factor in results]
		print("num: {}".format(len(jar_paths)))
		for path in jar_paths:
			parse_clazz_type(path, pro_class_info)

		with open(os.path.join(output_dir, "inner_and_third_party.pkl".format(bug_version)), "wb") as file:
			pickle.dump(pro_class_info, file)


if __name__ == "__main__":
	main()
