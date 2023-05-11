import os
import javalang
import shutil
import sys

if __name__ == "__main__":
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]
	anno_path = "../fault_localization/d4j_{}/{}/{}.txt".format(d4j_version, fl_setting, bug_version)
	output_dir = "../parsed_data/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version)
	data_dir = os.path.join(output_dir, "data/")
	anno_out_path = os.path.join(output_dir, "fl_no_empty.txt")
	src_out_path = os.path.join(output_dir, "src_no_cut.txt")
	string_out_path = os.path.join(output_dir, "string_table.txt")
	data_no_empty_dir = os.path.join(output_dir, "data_no_empty/")
	data_no_empty_no_anno_dir = os.path.join(output_dir, "data_no_empty_without_anno/")
	clazz_name_path = os.path.join(output_dir, "clazz_name.txt")
	clazz_name_no_empty_path = os.path.join(output_dir, "clazz_name_no_empty.txt")
	if not os.path.exists(data_no_empty_dir):
		os.makedirs(data_no_empty_dir)
	if not os.path.exists(data_no_empty_no_anno_dir):
		os.makedirs(data_no_empty_no_anno_dir)
	empty_list = []
	with open(src_out_path, "w") as out_file:
		with open(string_out_path, "w") as string_out_file:
			for i in range(len(os.listdir(data_dir))):
				index = i + 1
				with open(os.path.join(data_dir, "{}.txt".format(index)), "r") as file:
					content = file.read()
				if not content:
					empty_list.append(i)
					continue
				output = []
				string_list = []
				tokens = javalang.tokenizer.tokenize(content)
				flag = False
				for token in tokens:
					if token.value == "rank2fixstart":
						flag = True
					elif token.value == "rank2fixend":
						flag = False
					if type(token).__name__ == "String":
						output.append("\"STRING\"")
						if flag:
							string_list.append(token.value)
					else:
						output.append(token.value)
				out_file.write(" ".join(output) + "\n")
				string_out_file.write(" <split> ".join(string_list) + "\n")

	with open(anno_out_path, "w") as anno_out_file:
		with open(anno_path, "r") as file:
			annos = file.readlines()
		annos = [factor for i, factor in enumerate(annos) if i not in empty_list]
		anno_out_file.write("".join(annos))

	new_count = 1
	for i in range(len(os.listdir(data_dir))):
		if i not in empty_list:
			shutil.copy(os.path.join(data_dir, "{}.txt".format(i + 1)), os.path.join(data_no_empty_dir, "{}.txt".format(new_count)))
			new_count += 1

	for i in range(1, len(os.listdir(data_no_empty_dir)) + 1):
		with open(os.path.join(data_no_empty_dir, "{}.txt".format(i)), "r") as file:
			content = file.read()
			content = content.replace(" rank2fixstart ", "").replace(" rank2fixend ", "")
		with open(os.path.join(data_no_empty_no_anno_dir, "{}.txt".format(i)), "w") as file:
			file.write(content)

	with open(clazz_name_path, "r") as file:
		content = file.readlines()
	content_no_empty = [line.strip() for line in content if line.strip()]
	with open(clazz_name_no_empty_path, "w") as file:
		file.write("\n".join(content_no_empty))
