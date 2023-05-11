import sys
import os

if __name__ == "__main__":
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]
	beam_35 = int(sys.argv[4].strip())
	beam_single = int(sys.argv[5].strip())

	parsed_data_dir = "../parsed_data/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version)
	out_path = os.path.join(parsed_data_dir, "patch_irs.txt")
	combine_names = ["combine_35", "combine_single"]
	copy_names = ["copy_35", "copy_single"]
	beams = [beam_35, beam_single]
	final_15 = []
	final_single = []
	final_out = []
	for i in range(len(combine_names)):
		combine_name = combine_names[i]
		copy_name = copy_names[i]
		beam = beams[i]
		with open("../nmt_model/joint_inference/d4j_result/d4j_{}/{}/{}/{}.txt".format(d4j_version, fl_setting, bug_version, combine_name), "r") as file:
			content_combine = file.readlines()
			content_combine = [factor.strip() for factor in content_combine]
		with open("../nmt_model/origin_onmt/d4j_result/d4j_{}/{}/{}/{}.txt".format(d4j_version, fl_setting, bug_version, copy_name), "r") as file:
			content_copy = file.readlines()
			content_copy = [factor.strip() for factor in content_copy]

		assert len(content_combine) == len(content_copy)

		content_out = []
		step = 0
		while step * beam < len(content_combine):
			current_combine = content_combine[step * beam: (step + 1) * beam]
			current_copy = content_copy[step * beam: (step + 1) * beam]
			current_out = []
			for factor in current_combine:
				unk_count = 0
				for token in factor.split(" "):
					if token == "<unk>":
						unk_count += 1
				if unk_count <= 1:
					current_out.append(factor)
			for factor in current_copy:
				if len(current_out) >= beam:
					break
				if factor not in current_out:
					current_out.append(factor)
			current_out += [""] * (beam - len(current_out))
			if "single" in combine_name:
				final_single.append(current_out)
			else:
				final_15.append(current_out)
			step += 1

	for i in range(len(final_single)):
		final_out += final_15[i]
		final_out += final_single[i]
	with open(out_path, "w") as file:
		file.write("\n".join(final_out))
