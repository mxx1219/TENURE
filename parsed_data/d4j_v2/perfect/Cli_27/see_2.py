import pickle
import sys

with open("./result/patches_without_unk.pkl", "rb") as file:
	content = pickle.load(file)
print(len(content))

#key = int(input())
key = int(sys.argv[1]) - 1
while key != "q":
	print("\033[1;30;43m{}\033[0m".format(len(content[key])))
	for factor in content[key]:
		print("-"*20)
		print(factor)
	print("="*20)
	#key = int(input())
	break

