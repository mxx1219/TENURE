import javalang
import os
from parse_unk_type import parse_unk_type
from gen_ast import gen_ast
from find_gredients import *
from utils import *
from replace_unk import *
import pickle
import re
import sys


def main():
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]
	BEAM = int(sys.argv[4])

	parsed_data_dir = "../../parsed_data/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version)
	src_path = os.path.join(parsed_data_dir, "src_no_cut.txt")
	local_info_path = os.path.join(parsed_data_dir, "completion_info/local_info.pkl")
	global_info_path = os.path.join(parsed_data_dir, "completion_info/global_info.pkl")
	extra_global_info_path = os.path.join(parsed_data_dir, "completion_info/extra_global_info.pkl")
	out_dir = os.path.join(parsed_data_dir, "result/")
	input_path = os.path.join(out_dir, "patches_with_unk.pkl")
	out_path = os.path.join(out_dir, "patches_without_unk.pkl")

	with open(src_path, "r") as file:
		src_code = file.readlines()
		src_code = [line.strip() for line in src_code]
	with open(input_path, "rb") as file:
		pred_code = pickle.load(file)
	with open(local_info_path, "rb") as file:
		local_info = pickle.load(file)
	with open(global_info_path, "rb") as file:
		global_info = pickle.load(file)
	with open(extra_global_info_path, "rb") as file:
		extra_global_info = pickle.load(file)

	outputs = []
	for sample_index, tgt_method_code_list in enumerate(pred_code):
		i = sample_index
		print(i + 1)
		current_out_list = []
		for tmc in tgt_method_code_list:
			fake_clazz = "public class Tmp { " + tmc.replace("<unk>", "rank2fixunk") + " }"
			output_code = tmc
			try:
				tokens = javalang.tokenizer.tokenize(fake_clazz)
				parser = javalang.parser.Parser(tokens)
				root = parser.parse()
				root_node = gen_ast(root)
				unk_list = []
				find_unk_nodes(root_node, unk_list)
				ori_unk_count = len([substr for substr in re.finditer("<unk>", tmc)])
				if len(unk_list) == 0:
					current_out_list.append(tmc)
					continue
				elif len(unk_list) > 1:
					continue
				elif len(unk_list) != ori_unk_count:
					print("dismatch: {}, <unk>: {} vs ast unk: {}".format(i + 1, ori_unk_count, len(unk_list)))
				else:
					second_step_candidates = replace_for_also_unk_method(output_code, src_code[i//BEAM], global_info[i//BEAM], local_info[i//BEAM], extra_global_info[i//BEAM])
					current_out_list += second_step_candidates

			except (javalang.tokenizer.LexerError, javalang.parser.JavaSyntaxError, TypeError):
				print("syntax failed: {}".format(i + 1))

		outputs.append(current_out_list)

	with open(out_path, "wb") as file:
		pickle.dump(outputs, file)


if __name__ == "__main__":
	main()
