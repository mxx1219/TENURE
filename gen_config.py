import os


with open("./projects/v1.txt", "r") as file:
	content = file.readlines()
	content = [line.strip() for line in content]
for version in content:
	con_string = []
	con_string.append("d4j_version: v1")
	con_string.append("fl_setting: perfect")
	con_string.append("bug_version: {}".format(version))
	con_string.append("beam_all: 500")
	con_string.append("beam_35: 300")
	con_string.append("beam_single: 200")
	with open("./configs/{}.config".format(version), "w") as file:
		file.write("\n".join(con_string))
